# Copyright (c) 2026 kuro. All Rights Reserved.
"""Integration tests for the Sugar engine flow."""

from unittest.mock import MagicMock, patch
import pytest

from sugar.config import Config
from sugar.core.engine import Engine
from sugar.core.llm import LLMResponse


class TestIntegrationFlow:
    """Integration style tests for the core engine reasoning loop."""

    def setup_method(self) -> None:
        self.config = Config()
        self.config.ollama_model = "tinyllama:latest"
        
        with patch("sugar.core.engine.Memory"):
            self.engine = Engine(self.config)
            self.engine.memory = MagicMock()
            self.engine.current_conversation = "integrated_test"

    @patch("sugar.core.engine.LLM.chat")
    def test_multi_turn_successful_resolution(self, mock_chat: MagicMock) -> None:
        """Test a flow where tool output leads to a second tool call then final answer."""
        
        # 1. User asks a question
        # 2. LLM wants to search Obsidian
        # 3. Connector returns data
        # 4. LLM wants to search Web
        # 5. Connector returns data
        # 6. LLM gives final answer
        
        # Turn 1: Call Obsidian
        resp1 = LLMResponse(
            content="Checking notes.",
            tool_calls=[{"tool": "obsidian", "action": "list_notes", "params": {}}],
            raw='Check notes.\n```json\n{"tool": "obsidian", "action": "list_notes", "params": {}}\n```'
        )
        # Turn 2: Call Web after seeing notes
        resp2 = LLMResponse(
            content="Checking web.",
            tool_calls=[{"tool": "web", "action": "search", "params": {"query": "latest version"}}],
            raw='Check web.\n```json\n{"tool": "web", "action": "search", "params": {"query": "latest version"}}\n```'
        )
        # Turn 3: Final answer
        resp3 = LLMResponse(
            content="The latest version mentioned in your notes matches the web results.",
            tool_calls=[],
            raw="The latest version mentioned in your notes matches the web results."
        )
        
        mock_chat.side_effect = [resp1, resp2, resp3]
        
        # Mock Connectors
        mock_obsidian = MagicMock()
        mock_obsidian.name = "obsidian"
        mock_obsidian.is_configured.return_value = True
        mock_obsidian.execute.return_value = MagicMock(success=True, data="Found version 0.1.0")
        
        mock_web = MagicMock()
        mock_web.name = "web"
        mock_web.is_configured.return_value = True
        mock_web.execute.return_value = MagicMock(success=True, data="Web says 0.1.0")
        
        self.engine.register_connector(mock_obsidian)
        self.engine.register_connector(mock_web)
        
        # Execute
        final_response = self.engine.process_message("Verify version")
        
        assert final_response == "The latest version mentioned in your notes matches the web results."
        assert mock_chat.call_count == 3
        mock_obsidian.execute.assert_called_once()
        mock_web.execute.assert_called_once()

    @patch("sugar.core.engine.LLM.chat")
    def test_tool_error_handling_in_loop(self, mock_chat: MagicMock) -> None:
        """Test that if a tool fails, the error is fed back to the LLM."""
        
        resp1 = LLMResponse(
            content="Searching...",
            tool_calls=[{"tool": "web", "action": "search", "params": {"query": "foo"}}],
            raw='```json\n{"tool": "web", "action": "search", "params": {"query": "foo"}}\n```'
        )
        resp2 = LLMResponse(
            content="I couldn't search the web because of an error.",
            tool_calls=[],
            raw="Error reported."
        )
        mock_chat.side_effect = [resp1, resp2]
        
        mock_web = MagicMock()
        mock_web.name = "web"
        mock_web.is_configured.return_value = True
        mock_web.execute.return_value = MagicMock(success=False, data="Network Down")
        
        self.engine.register_connector(mock_web)
        
        response = self.engine.process_message("Search foo")
        
        assert "error" in response.lower() or "search" in response.lower()
        # Verify that the error message was sent back to LLM for turn 2
        args, _ = mock_chat.call_args_list[1]
        history = args[0]
        assert any("Network Down" in m["content"] for m in history)
