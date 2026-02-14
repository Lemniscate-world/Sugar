# Copyright (c) 2026 kuro. All Rights Reserved.
"""Targeted tests to close coverage gaps in Linear and API modules."""

from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

from sugar.connectors.linear import LinearConnector
from sugar.interfaces.gui_api import _check_ollama, _list_ollama_models, _read_env, _validate_vault


class TestCoverageGaps:
    """Tests specifically targeting previous 'miss' branches."""

    def test_read_env_missing_file(self) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            assert _read_env() == {}

    @patch("requests.get")
    def test_check_ollama_fail(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = Exception("Down")
        assert _check_ollama() is False

    @patch("requests.get")
    def test_list_ollama_models_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = Exception("Down")
        assert _list_ollama_models() == []

    def test_validate_vault_empty(self) -> None:
        assert _validate_vault("") is False
        assert _validate_vault(None) is False

    @patch("sugar.connectors.linear.requests.post")
    def test_linear_search_complex_results(self, mock_post: MagicMock) -> None:
        connector = LinearConnector("key")
        # Mock a rich response for _search_issues
        mock_post.return_value.json.return_value = {
            "data": {
                "issueSearch": {
                    "nodes": [
                        {
                            "identifier": "SUG-1",
                            "title": "Fix coverage",
                            "state": {"name": "In Progress"},
                            "assignee": {"name": "kuro"},
                            "description": "Short desc"
                        }
                    ]
                }
            }
        }
        
        result = connector.execute("search_issues", {"query": "coverage"})
        assert result.success is True
        assert "SUG-1" in result.data
        assert "kuro" in result.data

    @patch("requests.post")
    def test_linear_list_complex_results(self, mock_post: MagicMock) -> None:
        connector = LinearConnector("key")
        mock_post.return_value.json.return_value = {
            "data": {
                "issues": {
                    "nodes": [
                        {
                            "identifier": "SUG-2",
                            "title": "Bug",
                            "state": {"name": "Backlog"},
                            "priority": 1
                        }
                    ]
                }
            }
        }
        result = connector.execute("list_issues", {"limit": 1})
        assert result.success is True
        assert "SUG-2" in result.data

    @patch("sugar.connectors.linear.requests.post")
    def test_linear_create_issue_params(self, mock_post: MagicMock) -> None:
        # Test missing team/title branch
        # This will trigger teams query first if no team_id
        mock_post.return_value.json.return_value = {"data": {"teams": {"nodes": []}}}
        connector = LinearConnector("key")
        res = connector.execute("create_issue", {"title": "no team"})
        assert res.success is False
        assert "No teams found" in res.data

    def test_llm_extract_complex(self) -> None:
        from sugar.core.llm import LLM
        llm = LLM(MagicMock())
        content = (
            "Text before\n```json\n{\"tool\": \"t1\"}\n```\n"
            "Inside\n```json\n{\"tool\": \"t2\"}\n```\nText after"
        )
        calls = llm._extract_tool_calls(content)
        assert len(calls) == 2
        assert calls[0]["tool"] == "t1"
        assert calls[1]["tool"] == "t2"
