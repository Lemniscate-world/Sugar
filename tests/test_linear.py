"""Tests for the Linear connector (mocked API responses)."""

from unittest.mock import MagicMock, patch

from sugar.connectors.linear import LinearConnector


class TestLinearConnector:
    """Test Linear connector with mocked GraphQL responses."""

    def setup_method(self) -> None:
        self.connector = LinearConnector(api_key="test-key-123")

    def test_is_configured(self) -> None:
        assert self.connector.is_configured() is True
        empty = LinearConnector(api_key="")
        assert empty.is_configured() is False

    @patch("sugar.connectors.linear.requests.post")
    def test_list_issues(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "issues": {
                    "nodes": [
                        {
                            "id": "1",
                            "identifier": "BRN-1",
                            "title": "Setup project",
                            "state": {"name": "Done"},
                            "priority": 2,
                            "assignee": {"name": "kuro"},
                            "updatedAt": "2024-01-15",
                        },
                        {
                            "id": "2",
                            "identifier": "BRN-2",
                            "title": "Add Linear connector",
                            "state": {"name": "In Progress"},
                            "priority": 1,
                            "assignee": None,
                            "updatedAt": "2024-01-16",
                        },
                    ]
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.connector.execute("list_issues", {"limit": 5})
        assert result.success is True
        assert "BRN-1" in result.data
        assert "BRN-2" in result.data
        assert "Setup project" in result.data

    @patch("sugar.connectors.linear.requests.post")
    def test_search_issues(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "issueSearch": {
                    "nodes": [
                        {
                            "id": "1",
                            "identifier": "BRN-1",
                            "title": "Setup project",
                            "state": {"name": "Done"},
                            "assignee": {"name": "kuro"},
                            "description": "Initial project setup",
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.connector.execute("search_issues", {"query": "setup"})
        assert result.success is True
        assert "BRN-1" in result.data

    def test_search_missing_query(self) -> None:
        result = self.connector.execute("search_issues", {})
        assert result.success is False
        assert "Missing" in result.data

    @patch("sugar.connectors.linear.requests.post")
    def test_create_issue(self, mock_post: MagicMock) -> None:
        # First call: get teams
        teams_response = MagicMock()
        teams_response.json.return_value = {
            "data": {"teams": {"nodes": [{"id": "team-1", "name": "Brain"}]}}
        }
        teams_response.raise_for_status.return_value = None

        # Second call: create issue
        create_response = MagicMock()
        create_response.json.return_value = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "3",
                        "identifier": "BRN-3",
                        "title": "New feature",
                        "url": "https://linear.app/brain/issue/BRN-3",
                    },
                }
            }
        }
        create_response.raise_for_status.return_value = None

        mock_post.side_effect = [teams_response, create_response]

        result = self.connector.execute(
            "create_issue", {"title": "New feature", "description": "A great feature"}
        )
        assert result.success is True
        assert "BRN-3" in result.data

    def test_create_issue_missing_title(self) -> None:
        result = self.connector.execute("create_issue", {})
        assert result.success is False
        assert "Missing" in result.data

    @patch("requests.post")
    def test_list_issues_api_error(self, mock_post: MagicMock) -> None:
        mock_post.return_value.json.return_value = {"errors": [{"message": "Access denied"}]}
        
        result = self.connector.execute("list_issues", {})
        assert result.success is False
        assert "Access denied" in result.data

    @patch("requests.post")
    def test_create_issue_api_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = Exception("Connection Timeout")
        
        result = self.connector.execute("create_issue", {"title": "fail", "team": "T1"})
        assert result.success is False
        assert "Connection Timeout" in result.data

    def test_unknown_action(self) -> None:
        result = self.connector.execute("nonexistent_action", {})
        assert result.success is False
        assert "Unknown action" in result.data
