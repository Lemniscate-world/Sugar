# Copyright (c) 2026 kuro. All Rights Reserved.
"""Exhaustive tests for Linear and Obsidian actions to maximize coverage."""

from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

from sugar.connectors.linear import LinearConnector
from sugar.connectors.obsidian import ObsidianConnector
from sugar.interfaces.gui_api import _read_env, _check_ollama, _list_ollama_models


class TestActionCoverage:
    """Tests for complex action branches and error recovery."""

    @patch("sugar.connectors.linear.requests.post")
    def test_linear_list_projects(self, mock_post: MagicMock) -> None:
        mock_post.return_value.json.return_value = {
            "data": {
                "projects": {
                    "nodes": [{"name": "P1", "progress": 0.5, "state": "started"}]
                }
            }
        }
        connector = LinearConnector("key")
        result = connector.execute("list_projects", {})
        assert result.success is True
        assert "50%" in result.data

    @patch("sugar.connectors.linear.requests.post")
    def test_linear_list_teams(self, mock_post: MagicMock) -> None:
        mock_post.return_value.json.return_value = {
            "data": {
                "teams": {
                    "nodes": [{"name": "T1", "key": "ENG"}]
                }
            }
        }
        connector = LinearConnector("key")
        result = connector.execute("list_teams", {})
        assert result.success is True
        assert "ENG" in result.data

    @patch("sugar.connectors.linear.requests.post")
    def test_linear_update_issue_full(self, mock_post: MagicMock) -> None:
        # Mock workflow states and update success
        mock_post.return_value.json.side_effect = [
            {"data": {"workflowStates": {"nodes": [{"id": "s1", "name": "Done"}]}}},
            {"data": {"issueUpdate": {"success": True, "issue": {"identifier": "I-1", "title": "T", "state": {"name": "Done"}}}}}
        ]
        connector = LinearConnector("key")
        params = {"issue_id": "I-1", "title": "New", "state_name": "Done"}
        result = connector.execute("update_issue", params)
        assert result.success is True
        assert "Done" in result.data

    @patch("sugar.connectors.linear.requests.post")
    def test_linear_update_issue_invalid_state(self, mock_post: MagicMock) -> None:
        mock_post.return_value.json.return_value = {
            "data": {"workflowStates": {"nodes": [{"name": "Todo"}]}}
        }
        connector = LinearConnector("key")
        result = connector.execute("update_issue", {"issue_id": "I-1", "state_name": "Invalid"})
        assert result.success is False
        assert "Available" in result.data

    def test_obsidian_list_notes_empty(self) -> None:
        with patch("pathlib.Path.rglob", return_value=[]):
            connector = ObsidianConnector(Path("/tmp"))
            # is_dir must be true for is_configured
            with patch("pathlib.Path.is_dir", return_value=True):
                result = connector.execute("list_notes", {})
                assert result.success is True
                assert "No notes" in result.data

    @patch("sugar.core.llm.ollama.Client")
    def test_llm_chat_stream_partial_json(self, mock_client_cls: MagicMock) -> None:
        # This tests _extract_tool_calls indirectly if we used it in chat_stream 
        # but chat_stream returns raw chunks. 
        # But we can test _extract_tool_calls directly for partials.
        from sugar.core.llm import LLM
        llm = LLM(MagicMock())
        content = "```json\n{\"tool\": \"web\"" # Partial
        calls = llm._extract_tool_calls(content)
        assert len(calls) == 0

    def test_read_env_masking_short_values(self) -> None:
        from sugar.interfaces.gui_api import _read_env
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="API_KEY=123\n"):
                env = _read_env()
                assert env["API_KEY"] == "" # Logic: if len <= 4 return ""
