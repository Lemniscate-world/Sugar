# Copyright (c) 2026 kuro. All Rights Reserved.
"""Brain Engine — the central orchestrator that connects LLM, memory, and tools."""

from __future__ import annotations

import logging
from typing import Generator

from sugar.config import Config
from sugar.connectors.base import BaseConnector
from sugar.core.llm import LLM, LLMResponse
from sugar.core.memory import Memory

logger = logging.getLogger(__name__)


class Engine:
    """The Brain engine — routes user messages through LLM and tools.

    Flow: User message → load context from memory → build prompt with available tools
          → send to LLM → parse tool calls → execute tools → build final response
          → save to memory → return to user.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.llm = LLM(config)
        self.memory = Memory(config.db_path)
        self.connectors: dict[str, BaseConnector] = {}
        self.current_conversation: str | None = None

    def set_model(self, model: str) -> None:
        """Update the LLM model to use."""
        self.llm.model = model
        logger.info("Engine model set to: %s", model)

    def register_connector(self, connector: BaseConnector) -> None:
        """Register a connector for use by the engine."""
        if connector.is_configured():
            self.connectors[connector.name] = connector
            logger.info("Registered connector: %s", connector.name)
        else:
            logger.warning(
                "Connector '%s' not configured — skipping. "
                "Check your .env file.",
                connector.name,
            )

    def start_conversation(self, title: str = "") -> str:
        """Start a new conversation, returns conversation ID."""
        self.current_conversation = self.memory.new_conversation(title)
        logger.info("Started conversation: %s", self.current_conversation)
        return self.current_conversation

    def process_message(self, user_message: str) -> str:
        """Process a user message and return the brain's response.

        This is the main entry point for the engine.
        """
        # Ensure we have an active conversation
        if not self.current_conversation:
            self.start_conversation()

        if self.current_conversation is None:
             raise RuntimeError("Failed to start conversation")

        # Save user message
        self.memory.add_message(self.current_conversation, "user", user_message)

        # Build context from memory
        context_messages = self.memory.get_context_messages(
            self.current_conversation, limit=20
        )

        # Build enhanced system prompt with tool descriptions
        system_prompt = self._build_system_prompt()

        # Send to LLM
        llm_response = self.llm.chat(context_messages, system_prompt=system_prompt)

        # Process tool calls if any
        if llm_response.has_tool_calls:
            final_response = self._process_tool_calls(
                llm_response, context_messages, system_prompt
            )
        else:
            final_response = llm_response.content

        # Save assistant response
        self.memory.add_message(self.current_conversation, "assistant", final_response)

        return final_response

    def _build_system_prompt(self) -> str:
        """Build the system prompt including available connector descriptions."""
        base_prompt = self.config.system_prompt

        if not self.connectors:
            return base_prompt

        connector_docs = "\n\n## Available Tools\n\n"
        for connector in self.connectors.values():
            connector_docs += connector.describe_for_llm() + "\n\n"

        connector_docs += (
            "\nTo use a tool, include a JSON block in your response like this:\n"
            "```json\n"
            '{"tool": "connector_name", "action": "action_name", "params": {"key": "value"}}\n'
            "```\n"
            "You can use multiple tools in one response. After using a tool, "
            "explain the result to the user in natural language."
        )

        return base_prompt + connector_docs

    def _process_tool_calls(
        self,
        llm_response: LLMResponse,
        context_messages: list[dict[str, str]],
        system_prompt: str,
    ) -> str:
        """Execute tool calls and get a final response from the LLM."""
        tool_results = []

        for call in llm_response.tool_calls:
            tool_name = call.get("tool", "")
            action = call.get("action", "")
            params = call.get("params", {})

            logger.info("Tool call: %s.%s(%s)", tool_name, action, params)

            connector = self.connectors.get(tool_name)
            if not connector:
                tool_results.append(
                    f"⚠️ Unknown tool: '{tool_name}'. "
                    f"Available: {list(self.connectors.keys())}"
                )
                continue

            result = connector.execute(action, params)
            status = "✅" if result.success else "❌"
            tool_results.append(f"{status} {tool_name}.{action}:\n{result.data}")

        # Send tool results back to the LLM for a natural language summary
        tool_context = "\n\n".join(tool_results)
        follow_up_messages = context_messages + [
            {"role": "assistant", "content": llm_response.raw},
            {
                "role": "user",
                "content": (
                    f"Here are the results from the tools you called:\n\n{tool_context}\n\n"
                    "Now provide a helpful, natural language response to the user based on "
                    "these results. Do NOT include any JSON tool calls in your response."
                ),
            },
        ]

        final_response = self.llm.chat(follow_up_messages, system_prompt=system_prompt)
        return final_response.content or tool_context

    def process_message_stream(self, user_message: str) -> Generator[str, None, None]:
        """Process a message and yield chunks (streaming).

        Handles tool calls by streaming the initial request, execution status,
        and final response sequentially in a multi-turn loop.
        """
        if not self.current_conversation:
            self.start_conversation()

        if self.current_conversation is None:
            raise RuntimeError("Failed to start conversation")

        # Save user message
        self.memory.add_message(self.current_conversation, "user", user_message)
        context_messages = self.memory.get_context_messages(
            self.current_conversation, limit=20
        )
        system_prompt = self._build_system_prompt()

        current_messages = list(context_messages)
        depth = 0
        MAX_DEPTH = 5

        while depth < MAX_DEPTH:
            depth += 1
            full_response = ""
            
            # 1. Get LLM response
            try:
                stream = self.llm.chat_stream(current_messages, system_prompt=system_prompt)
                for chunk in stream:
                    full_response += chunk
                    yield chunk
            except Exception as e:
                logger.error("Error in stream pass: %s", e)
                yield f"\n⚠️ Error: {e}"
                break

            # Save assistant response to memory and local context
            self.memory.add_message(self.current_conversation, "assistant", full_response)
            current_messages.append({"role": "assistant", "content": full_response})

            # 2. Check for tool calls
            tool_calls = self.llm._extract_tool_calls(full_response)
            if not tool_calls:
                break

            # 3. Process Tools
            yield "\n\n"
            tool_results = []
            
            for call in tool_calls:
                tool_name = call.get("tool", "")
                action = call.get("action", "")
                params = call.get("params", {})
                
                yield f"*Executing {tool_name}.{action}...* "
                
                connector = self.connectors.get(tool_name)
                if not connector:
                    res = f"⚠️ Unknown tool: '{tool_name}'"
                    tool_results.append(res)
                    yield f"{res}\n"
                    continue

                try:
                    result = connector.execute(action, params)
                    status = "✅" if result.success else "❌"
                    res_text = f"{status} Call: {tool_name}.{action}\nResult: {result.data}"
                    tool_results.append(res_text)
                    yield f"{status}\n"
                except Exception as e:
                    logger.error("Tool execution failed: %s", e)
                    yield f"❌ Error: {e}\n"
                    tool_results.append(f"Tool {tool_name} error: {e}")

            # 4. Prepare feedback for next pass
            tool_context = "\n\n".join(tool_results)
            feedback = (
                f"Results from previous tool calls:\n\n{tool_context}\n\n"
                "Analyze these results. If you have the answer, respond to the user. "
                "If you need more information, use another tool call."
            )
            current_messages.append({"role": "user", "content": feedback})
            yield "\n---\n"

        if depth >= MAX_DEPTH:
            yield "\n⚠️ Maximum reasoning depth reached."

    def get_status(self) -> dict:
        """Get the current engine status."""
        return {
            "llm_available": self.llm.is_available(),
            "model": self.config.ollama_model,
            "connectors": {
                name: conn.is_configured() for name, conn in self.connectors.items()
            },
            "active_conversation": self.current_conversation,
        }

