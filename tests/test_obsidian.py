"""Tests for the Obsidian connector (filesystem-based note operations)."""

from pathlib import Path
import tempfile

from sugar.connectors.obsidian import ObsidianConnector


class TestObsidianConnector:
    """Test Obsidian vault operations against a temp directory."""

    def setup_method(self) -> None:
        """Create a temporary vault for each test."""
        self.tmp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.tmp_dir)
        self.connector = ObsidianConnector(self.vault_path)

        # Create some test notes
        (self.vault_path / "daily").mkdir()
        (self.vault_path / "projects").mkdir()

        (self.vault_path / "README.md").write_text("# My Vault\nWelcome to my vault.")
        (self.vault_path / "daily" / "2024-01-15.md").write_text(
            "# Jan 15\n- Met with team about Linear integration\n- Reviewed PRs"
        )
        (self.vault_path / "projects" / "sugar.md").write_text(
            "# Brain Project\nAI assistant that connects tools."
        )

    def test_is_configured(self) -> None:
        assert self.connector.is_configured() is True
        unconfigured = ObsidianConnector(None)
        assert unconfigured.is_configured() is False

    def test_search_notes_by_filename(self) -> None:
        result = self.connector.execute("search_notes", {"query": "sugar"})
        assert result.success is True
        assert "sugar.md" in result.data

    def test_search_notes_by_content(self) -> None:
        result = self.connector.execute("search_notes", {"query": "Linear integration"})
        assert result.success is True
        assert "2024-01-15" in result.data

    def test_read_note(self) -> None:
        result = self.connector.execute("read_note", {"path": "projects/sugar.md"})
        assert result.success is True
        assert "Brain Project" in result.data

    def test_read_note_not_found(self) -> None:
        result = self.connector.execute("read_note", {"path": "nonexistent.md"})
        assert result.success is False

    def test_create_note(self) -> None:
        result = self.connector.execute(
            "create_note",
            {"path": "ideas/new-idea.md", "content": "# New Idea\nThis could be great."},
        )
        assert result.success is True
        assert (self.vault_path / "ideas" / "new-idea.md").exists()

        content = (self.vault_path / "ideas" / "new-idea.md").read_text()
        assert "New Idea" in content
        assert "created:" in content  # Has frontmatter

    def test_create_note_already_exists(self) -> None:
        result = self.connector.execute(
            "create_note",
            {"path": "README.md", "content": "Overwrite attempt"},
        )
        assert result.success is False
        assert "already exists" in result.data

    def test_append_to_note(self) -> None:
        result = self.connector.execute(
            "append_to_note",
            {"path": "projects/sugar.md", "content": "Added web search support."},
        )
        assert result.success is True

        content = (self.vault_path / "projects" / "sugar.md").read_text()
        assert "Added web search support" in content

    def test_list_notes(self) -> None:
        result = self.connector.execute("list_notes", {})
        assert result.success is True
        assert "README.md" in result.data

    def test_list_notes_subdirectory(self) -> None:
        result = self.connector.execute("list_notes", {"directory": "daily"})
        assert result.success is True
        assert "2024-01-15" in result.data

    def test_search_no_results(self) -> None:
        result = self.connector.execute(
            "search_notes", {"query": "xyznonexistentquery"}
        )
        assert result.success is True
        assert "No notes found" in result.data

    def test_missing_params(self) -> None:
        result = self.connector.execute("read_note", {})
        assert result.success is False
        assert "Missing 'path'" in result.data

    def test_create_note_permission_error(self) -> None:
        with patch("pathlib.Path.write_text") as mock_write:
            mock_write.side_effect = PermissionError("Permission denied")
            params = {"path": "restricted.md", "content": "secret"}
            result = self.connector.execute("create_note", params)
            assert result.success is False
            assert "Permission denied" in result.data
            
    def test_append_note_not_found(self) -> None:
        params = {"path": "missing.md", "content": "test"}
        result = self.connector.execute("append_to_note", params)
        assert result.success is False
        assert "does not exist" in result.data
