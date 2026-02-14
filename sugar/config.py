"""Brain configuration — loads settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Central configuration for the Brain application."""

    # Ollama
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "mistral"))
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )

    # Linear
    linear_api_key: str = field(default_factory=lambda: os.getenv("LINEAR_API_KEY", ""))

    # Obsidian
    obsidian_vault_path: Path | None = field(default=None)

    # Telegram
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))

    # Memory
    db_path: Path = field(default_factory=lambda: Path("brain_memory.db"))

    # System prompt for the LLM
    system_prompt: str = field(default="")

    def __post_init__(self) -> None:
        """Post-initialization: resolve paths and set defaults."""
        # Obsidian vault
        vault_env = os.getenv("OBSIDIAN_VAULT_PATH", "")
        if vault_env and self.obsidian_vault_path is None:
            self.obsidian_vault_path = Path(vault_env).expanduser().resolve()

        # System prompt
        if not self.system_prompt:
            self.system_prompt = self._default_system_prompt()

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "You are Brain, a personal AI assistant that helps manage tasks, notes, "
            "and projects. You have access to tools that let you interact with:\n"
            "- **Linear**: Project management (issues, projects, updates)\n"
            "- **Obsidian**: Personal knowledge base (notes, ideas)\n"
            "- **Web Search**: Finding information online\n\n"
            "When the user asks you to do something, use the appropriate tool. "
            "Be concise, helpful, and proactive. If you can't do something, say so clearly.\n\n"
            "IMPORTANT: When you need to use a tool, respond with a JSON tool call in this format:\n"
            '```json\n{"tool": "connector_name", "action": "action_name", "params": {...}}\n```\n'
            "Available connectors and their actions will be listed for you."
        )

    @property
    def linear_enabled(self) -> bool:
        return bool(self.linear_api_key)

    @property
    def obsidian_enabled(self) -> bool:
        return self.obsidian_vault_path is not None and self.obsidian_vault_path.is_dir()

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token)

    def load_dotenv(self, env_path: Path | None = None) -> None:
        """Load environment variables from a .env file (simple parser, no deps)."""
        path = env_path or Path(".env")
        if not path.exists():
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
        # Re-init with new env vars
        self.__init__()  # type: ignore[misc]
