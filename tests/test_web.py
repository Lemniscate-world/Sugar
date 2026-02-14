# Copyright (c) 2026 kuro. All Rights Reserved.
"""Tests for the Web search connector."""

from unittest.mock import MagicMock, patch
import pytest

from sugar.connectors.web import WebConnector


class TestWebConnector:
    """Test suite for the WebConnector."""

    def setup_method(self) -> None:
        self.connector = WebConnector()

    def test_name_and_description(self) -> None:
        assert self.connector.name == "web"
        assert "DuckDuckGo" in self.connector.description

    def test_is_configured(self) -> None:
        assert self.connector.is_configured() is True

    @patch("duckduckgo_search.DDGS")
    def test_search_success(self, mock_ddgs_class: MagicMock) -> None:
        # Mocking the context manager: DDGS() as ddgs
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
        
        # Mock results
        mock_ddgs.text.return_value = [
            {"title": "Ollama", "body": "Local LLM runner", "href": "https://ollama.com"},
            {"title": "DeepSeek", "body": "Powerful model", "href": "https://deepseek.com"}
        ]
        
        params = {"query": "AI news", "max_results": 2}
        result = self.connector.execute("search", params)
        
        assert result.success is True
        assert "Ollama" in result.data
        assert "DeepSeek" in result.data
        assert len(result.raw) == 2
        mock_ddgs.text.assert_called_once_with("AI news", max_results=2)

    @patch("duckduckgo_search.DDGS")
    def test_search_no_results(self, mock_ddgs_class: MagicMock) -> None:
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
        mock_ddgs.text.return_value = []
        
        params = {"query": "nonexistent query"}
        result = self.connector.execute("search", params)
        
        assert result.success is True
        assert "No results" in result.data

    @patch("duckduckgo_search.DDGS")
    def test_news_success(self, mock_ddgs_class: MagicMock) -> None:
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
        mock_ddgs.news.return_value = [
            {"title": "New AI release", "body": "Big news", "url": "https://news.com", "date": "2024-02-14"}
        ]
        
        params = {"query": "Ollama", "max_results": 1}
        result = self.connector.execute("news", params)
        
        assert result.success is True
        assert "New AI release" in result.data
        assert len(result.raw) == 1
        mock_ddgs.news.assert_called_once_with("Ollama", max_results=1)

    def test_search_missing_query(self) -> None:
        result = self.connector.execute("search", {})
        assert result.success is False
        assert "Missing 'query'" in result.data

    @patch("duckduckgo_search.DDGS")
    def test_search_error(self, mock_ddgs_class: MagicMock) -> None:
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
        mock_ddgs.text.side_effect = Exception("DDG rate limit")
        
        params = {"query": "fail"}
        result = self.connector.execute("search", params)
        
        assert result.success is False
        assert "Search error" in result.data
