# Copyright (c) 2026 kuro. All Rights Reserved.
"""Base connector interface — all connectors inherit from this."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of a connector action."""

    success: bool
    data: str  # Human-readable result for the LLM
    raw: dict | list | None = None  # Raw data if needed


class BaseConnector(ABC):
    """Abstract base class for all Brain connectors.

    Each connector represents an external tool (Linear, Obsidian, web, etc.).
    Subclasses must implement:
        - name: unique identifier
        - description: what this connector does (shown to the LLM)
        - available_actions(): list of actions with descriptions
        - execute(action, params): perform an action
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique connector name (e.g., 'linear', 'obsidian')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """What this connector does (shown to the LLM to help it decide when to use it)."""
        ...

    @abstractmethod
    def available_actions(self) -> list[dict[str, str]]:
        """Return list of available actions.

        Each action is a dict with:
            - name: action identifier
            - description: what it does
            - params: description of required parameters
        """
        ...

    @abstractmethod
    def execute(self, action: str, params: dict) -> ActionResult:
        """Execute an action with the given parameters.

        Args:
            action: The action name (must be one from available_actions).
            params: Parameters for the action.

        Returns:
            ActionResult with success status and human-readable data.
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this connector has the required configuration to work."""
        ...

    def describe_for_llm(self) -> str:
        """Generate a description of this connector for the LLM system prompt."""
        actions = self.available_actions()
        action_lines = []
        for a in actions:
            action_lines.append(f"  - `{a['name']}`: {a['description']}")
            if a.get("params"):
                action_lines.append(f"    Parameters: {a['params']}")

        return (
            f"### {self.name}\n"
            f"{self.description}\n"
            f"Actions:\n" + "\n".join(action_lines)
        )
