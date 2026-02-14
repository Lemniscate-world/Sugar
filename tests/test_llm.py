"""Tests for the LLM module (Ollama wrapper)."""

from unittest.mock import MagicMock, patch

from sugar.config import Config
from sugar.core.llm import LLM


class TestLLMToolParsing:
    """Test tool call extraction from LLM responses."""

    def setup_method(self) -> None:
        self.config = Config()
        self.llm = LLM(self.config)

    def test_extract_single_tool_call(self) -> None:
        content = (
            "Let me search for that.\n"
            '```json\n{"tool": "linear", "action": "list_issues", "params": {"limit": 5}}\n```\n'
            "I'll show you the results."
        )
        calls = self.llm._extract_tool_calls(content)
        assert len(calls) == 1
        assert calls[0]["tool"] == "linear"
        assert calls[0]["action"] == "list_issues"
        assert calls[0]["params"]["limit"] == 5

    def test_extract_multiple_tool_calls(self) -> None:
        content = (
            "Let me check both.\n"
            '```json\n{"tool": "linear", "action": "list_issues", "params": {}}\n```\n'
            "And also:\n"
            '```json\n{"tool": "obsidian", "action": "search_notes", "params": {"query": "test"}}\n```\n'
        )
        calls = self.llm._extract_tool_calls(content)
        assert len(calls) == 2

    def test_no_tool_calls(self) -> None:
        content = "Here's a regular response with no tools."
        calls = self.llm._extract_tool_calls(content)
        assert len(calls) == 0

    def test_invalid_json_ignored(self) -> None:
        content = '```json\n{broken json}\n```\nBut I can still help.'
        calls = self.llm._extract_tool_calls(content)
        assert len(calls) == 0

    def test_non_tool_json_ignored(self) -> None:
        content = '```json\n{"name": "Alice", "age": 30}\n```\n'
        calls = self.llm._extract_tool_calls(content)
        assert len(calls) == 0  # No "tool" key

    def test_clean_response(self) -> None:
        content = (
            "Looking it up.\n"
            '```json\n{"tool": "web", "action": "search", "params": {"query": "test"}}\n```\n'
            "Done!"
        )
        cleaned = self.llm._clean_response(content)
        assert "tool" not in cleaned
        assert "Looking it up" in cleaned
        assert "Done!" in cleaned

    @patch("sugar.core.llm.ollama.Client")
    def test_chat_stream_success(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        def mock_gen():
            yield {"message": {"content": "Hello"}}
            yield {"message": {"content": " world"}}
            
        mock_client.chat.return_value = mock_gen()
        
        llm = LLM(self.config)
        chunks = list(llm.chat_stream([{"role": "user", "content": "hi"}]))
        assert chunks == ["Hello", " world"]

    @patch("sugar.core.llm.ollama.Client")
    def test_is_available_true(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Mocking model list
        mock_model = MagicMock()
        mock_model.model = "tinyllama:latest"
        mock_resp = MagicMock()
        mock_resp.models = [mock_model]
        mock_client.list.return_value = mock_resp
        
    @patch("sugar.core.llm.ollama.Client")
    def test_is_available_false(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.list.side_effect = Exception("Service Down")
        
        llm = LLM(self.config)
        assert llm.is_available() is False

    @patch("sugar.core.llm.ollama.Client")
    def test_chat_stream_error(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.side_effect = Exception("Stream interrupted")
        
        llm = LLM(self.config)
        chunks = list(llm.chat_stream([{"role": "user", "content": "hi"}]))
        assert len(chunks) == 1
        assert "stream error" in chunks[0].lower()
