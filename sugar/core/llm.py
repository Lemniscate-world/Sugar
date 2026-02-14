"""Ollama LLM wrapper — handles communication with the local Ollama instance."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import ollama

from sugar.config import Config

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from the LLM."""

    content: str
    tool_calls: list[dict]  # Parsed tool call requests from the LLM output
    raw: str

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLM:
    """Thin wrapper around the Ollama Python client."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = ollama.Client(host=config.ollama_host)
        self.model = config.ollama_model

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send messages to Ollama and get a response.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."} dicts.
            system_prompt: Optional system prompt override.

        Returns:
            LLMResponse with parsed content and any tool calls.
        """
        full_messages = []

        # Add system prompt
        prompt = system_prompt or self.config.system_prompt
        if prompt:
            full_messages.append({"role": "system", "content": prompt})

        full_messages.extend(messages)

        try:
            response = self.client.chat(
                model=self.model,
                messages=full_messages,
            )
            raw_content = response.message.content or ""
            logger.debug("LLM raw response: %s", raw_content[:200])

            # Parse tool calls from the response
            tool_calls = self._extract_tool_calls(raw_content)
            clean_content = self._clean_response(raw_content)

            return LLMResponse(
                content=clean_content,
                tool_calls=tool_calls,
                raw=raw_content,
            )

        except ollama.ResponseError as e:
            logger.error("Ollama error: %s", e)
            return LLMResponse(
                content=f"⚠️ LLM Error: {e}",
                tool_calls=[],
                raw=str(e),
            )
        except Exception as e:
            logger.error("Unexpected LLM error: %s", e)
            return LLMResponse(
                tool_calls=[],
                raw=str(e),
            )

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ):
        """Send messages to Ollama and stream the response.

        Yields:
            str: Token chunks from the LLM.
        """
        full_messages = []

        # Add system prompt
        prompt = system_prompt or self.config.system_prompt
        if prompt:
            full_messages.append({"role": "system", "content": prompt})

        full_messages.extend(messages)

        try:
            stream = self.client.chat(
                model=self.model,
                messages=full_messages,
                stream=True,
            )
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

        except Exception as e:
            logger.error("LLM Stream Error: %s", e)
            yield f"\n⚠️ Stream Error: {e}"

    def _extract_tool_calls(self, content: str) -> list[dict]:
        """Extract JSON tool calls from the LLM response.

        Looks for ```json blocks containing tool/action/params structure.
        """
        tool_calls = []

        # Match ```json ... ``` blocks
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", content, re.DOTALL)

        for block in json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and "tool" in data and "action" in data:
                    tool_calls.append(data)
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON block: %s", block[:100])

        return tool_calls

    def _clean_response(self, content: str) -> str:
        """Remove tool call JSON blocks from the response for display."""
        # Remove ```json ... ``` blocks that contain tool calls
        cleaned = re.sub(r"```json\s*\{[^}]*\"tool\"[^}]*\}.*?```", "", content, flags=re.DOTALL)
        return cleaned.strip()

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            models = self.client.list()
            available = [m.model for m in models.models]
            if self.model in available or any(self.model in m for m in available):
                return True
            logger.warning(
                "Model '%s' not found. Available: %s", self.model, available
            )
            return False
        except Exception as e:
            logger.error("Cannot connect to Ollama: %s", e)
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            models = self.client.list()
            return [m.model for m in models.models]
        except Exception:
            return []
