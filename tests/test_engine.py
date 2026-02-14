# Copyright (c) 2026 kuro. All Rights Reserved.
"""Tests for the Engine module."""

from unittest.mock import MagicMock, patch
import pytest

from sugar.config import Config
from sugar.core.engine import Engine
from sugar.core.llm import LLMResponse


class TestEngine:
    """Test suite for the Engine orchestrator."""

    def setup_method(self) -> None:
        self.config = Config()
        # Mock Memory to avoid DB files during tests
        with patch("sugar.core.engine.Memory") as mock_memory_cls:
            self.engine = Engine(self.config)
            self.engine.memory = MagicMock()
            # Set a fake conversation ID
            self.engine.current_conversation = "test_conv_id"

    def test_register_connector(self) -> None:
        mock_connector = MagicMock()
        mock_connector.name = "test_tool"
        mock_connector.is_configured.return_value = True
        
        self.engine.register_connector(mock_connector)
        assert "test_tool" in self.engine.connectors
        assert self.engine.connectors["test_tool"] == mock_connector

    def test_register_unconfigured_connector(self) -> None:
        mock_connector = MagicMock()
        mock_connector.name = "unconfigured_tool"
        mock_connector.is_configured.return_value = False
        
        self.engine.register_connector(mock_connector)
        assert "unconfigured_tool" not in self.engine.connectors

    @patch("sugar.core.engine.LLM.chat")
    def test_process_message_no_tools(self, mock_chat: MagicMock) -> None:
        # Mock LLM response with no tool calls
        mock_chat.return_value = LLMResponse(
            content="Hello world",
            tool_calls=[],
            raw="Hello world"
        )
        
        response = self.engine.process_message("Hi")
        assert response == "Hello world"
        self.engine.memory.add_message.assert_called()

    @patch("sugar.core.engine.LLM.chat")
    def test_process_message_with_tools(self, mock_chat: MagicMock) -> None:
        # 1. Mock first LLM response with a tool call
        resp1 = LLMResponse(
            content="Let me check Obsidian.",
            tool_calls=[{"tool": "obsidian", "action": "search_notes", "params": {"query": "test"}}],
            raw='Let me check Obsidian.\n```json\n{"tool": "obsidian", "action": "search_notes", "params": {"query": "test"}}\n```'
        )
        # 2. Mock second LLM response (summarization)
        resp2 = LLMResponse(
            content="I found 2 notes.",
            tool_calls=[],
            raw="I found 2 notes."
        )
        mock_chat.side_effect = [resp1, resp2]
        
        # Mock connector
        mock_obsidian = MagicMock()
        mock_obsidian.name = "obsidian"
        mock_obsidian.is_configured.return_value = True
        result_mock = MagicMock()
        result_mock.success = True
        result_mock.data = "Note 1, Note 2"
        mock_obsidian.execute.return_value = result_mock
        
        self.engine.register_connector(mock_obsidian)
        
        response = self.engine.process_message("Search notes")
        
        assert response == "I found 2 notes."
        mock_obsidian.execute.assert_called_once()
        assert mock_chat.call_count == 2

    @patch("sugar.core.engine.LLM.chat_stream")
    def test_process_message_stream_no_tools(self, mock_chat_stream: MagicMock) -> None:
        # Mock stream generator
        def stream_gen(*args, **kwargs):
            yield "Hello "
            yield "stream"
            
        mock_chat_stream.side_effect = stream_gen
        
        # We need to mock _extract_tool_calls because it's called on the full response
        with patch.object(self.engine.llm, "_extract_tool_calls", return_value=[]):
            chunks = list(self.engine.process_message_stream("Hi"))
            assert "".join(chunks) == "Hello stream"

    def test_get_status(self) -> None:
        with patch.object(self.engine.llm, "is_available", return_value=True):
            status = self.engine.get_status()
            assert status["llm_available"] is True
            assert status["active_conversation"] == "test_conv_id"
