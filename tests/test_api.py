# Copyright (c) 2026 kuro. All Rights Reserved.
"""Tests for the GUI API (FastAPI)."""

from unittest.mock import MagicMock, patch
import pytest
import json
from fastapi.testclient import TestClient

from sugar.interfaces.gui_api import app


class TestAPI:
    """Test suite for the FastAPI endpoints."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    @patch("sugar.interfaces.gui_api.engine")
    @patch("sugar.interfaces.gui_api._check_ollama")
    @patch("sugar.interfaces.gui_api._is_ollama_installed")
    def test_get_status(self, mock_installed: MagicMock, mock_check: MagicMock, mock_engine: MagicMock) -> None:
        mock_installed.return_value = True
        mock_check.return_value = True
        mock_engine.get_status.return_value = {"active_conversation": None}
        
        response = self.client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "ollama" in data
        assert data["ollama"]["running"] is True
        assert "engine" in data

    @patch("sugar.interfaces.gui_api.engine")
    def test_list_conversations(self, mock_engine: MagicMock) -> None:
        mock_engine.memory.list_conversations.return_value = [
            {"id": "conv1", "title": "First chat"}
        ]
        
        response = self.client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert data["conversations"][0]["id"] == "conv1"

    @patch("sugar.interfaces.gui_api.engine")
    def test_new_conversation(self, mock_engine: MagicMock) -> None:
        mock_engine.memory.new_conversation.return_value = "new_id"
        
        response = self.client.post("/api/conversations")
        assert response.status_code == 200
        assert response.json()["id"] == "new_id"

    @patch("sugar.interfaces.gui_api.engine")
    def test_save_config(self, mock_engine: MagicMock) -> None:
        payload = {
            "ollama_model": "llama3",
            "ollama_host": "http://localhost:11434",
            "linear_api_key": "test_key",
            "obsidian_vault_path": "/test/vault"
        }
        # In the real API, this writes a file. Let's mock the file write or just check the logic.
        with patch("pathlib.Path.write_text") as mock_write:
            response = self.client.post("/api/config/save", json=payload)
            assert response.status_code == 200
            assert response.json()["success"] is True
            mock_write.assert_called()

    @patch("sugar.interfaces.gui_api.engine")
    def test_chat_stream_endpoint(self, mock_engine: MagicMock) -> None:
        mock_engine.start_conversation.return_value = "test_cid"
        
        def mock_stream(msg):
            yield "Hello"
            
        mock_engine.process_message_stream.side_effect = mock_stream
        
        payload = {
            "messages": [{"role": "user", "content": "hi"}],
            "model": "tinyllama"
        }
        
        response = self.client.post("/api/chat/stream", json=payload)
        assert response.status_code == 200
        
        # Verify content
        lines = [line.decode("utf-8") if isinstance(line, bytes) else line for line in response.iter_lines()]
        assert any("test_cid" in line for line in lines)
        assert any("Hello" in line for line in lines)
        assert any("[DONE]" in line for line in lines)

    def test_health_check(self) -> None:
        response = self.client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
