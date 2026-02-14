"""Obsidian connector — read, search, and write markdown notes in an Obsidian vault."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sugar.connectors.base import ActionResult, BaseConnector

logger = logging.getLogger(__name__)


class ObsidianConnector(BaseConnector):
    """Connector for Obsidian vaults (local markdown files).

    Obsidian vaults are just directories of .md files. This connector
    reads, searches, creates, and appends to notes directly on the filesystem.
    """

    def __init__(self, vault_path: Path | None) -> None:
        self.vault_path = vault_path

    @property
    def name(self) -> str:
        return "obsidian"

    @property
    def description(self) -> str:
        return (
            "Obsidian personal knowledge base. Use this to search notes, "
            "read note contents, create new notes, or append to existing notes."
        )

    def is_configured(self) -> bool:
        return self.vault_path is not None and self.vault_path.is_dir()

    def available_actions(self) -> list[dict[str, str]]:
        return [
            {
                "name": "search_notes",
                "description": "Search notes by filename or content",
                "params": "query (required: search text)",
            },
            {
                "name": "read_note",
                "description": "Read the full content of a note",
                "params": "path (required: relative path within vault, e.g. 'Projects/my-idea.md')",
            },
            {
                "name": "create_note",
                "description": "Create a new note in the vault",
                "params": "path (required: relative path), content (required: note content in markdown)",
            },
            {
                "name": "append_to_note",
                "description": "Append content to an existing note",
                "params": "path (required: relative path), content (required: text to append)",
            },
            {
                "name": "list_notes",
                "description": "List notes in a directory of the vault",
                "params": "directory (optional: subdirectory to list, defaults to root), "
                "limit (optional, default 20)",
            },
        ]

    def execute(self, action: str, params: dict) -> ActionResult:
        if not self.is_configured():
            return ActionResult(
                success=False,
                data="Obsidian vault not configured. Set OBSIDIAN_VAULT_PATH in .env",
            )

        handlers = {
            "search_notes": self._search_notes,
            "read_note": self._read_note,
            "create_note": self._create_note,
            "append_to_note": self._append_to_note,
            "list_notes": self._list_notes,
        }
        handler = handlers.get(action)
        if not handler:
            return ActionResult(success=False, data=f"Unknown action: {action}")
        try:
            return handler(params)
        except Exception as e:
            logger.error("Obsidian %s failed: %s", action, e)
            return ActionResult(success=False, data=f"Error: {e}")

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path within the vault, with safety checks."""
        assert self.vault_path is not None
        full_path = (self.vault_path / relative_path).resolve()
        # Security: ensure we stay within the vault
        if not str(full_path).startswith(str(self.vault_path.resolve())):
            raise ValueError("Path traversal detected — must stay within vault.")
        return full_path

    def _search_notes(self, params: dict) -> ActionResult:
        query = params.get("query", "").lower()
        if not query:
            return ActionResult(success=False, data="Missing 'query' parameter.")

        assert self.vault_path is not None
        results = []

        for md_file in self.vault_path.rglob("*.md"):
            relative = md_file.relative_to(self.vault_path)
            # Skip hidden directories
            if any(part.startswith(".") for part in relative.parts):
                continue

            # Search filename
            if query in md_file.stem.lower():
                results.append({"path": str(relative), "match": "filename"})
                continue

            # Search content
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if query in content.lower():
                    # Find matching line for context
                    for line in content.split("\n"):
                        if query in line.lower():
                            results.append({
                                "path": str(relative),
                                "match": "content",
                                "context": line.strip()[:100],
                            })
                            break
            except OSError:
                continue

            if len(results) >= 20:
                break

        if not results:
            return ActionResult(success=True, data=f"No notes found matching '{query}'.")

        lines = []
        for r in results:
            ctx = f" — \"{r['context']}\"" if r.get("context") else ""
            lines.append(f"- `{r['path']}` ({r['match']}){ctx}")

        return ActionResult(
            success=True,
            data=f"Found {len(results)} notes matching '{query}':\n" + "\n".join(lines),
            raw=results,
        )

    def _read_note(self, params: dict) -> ActionResult:
        path_str = params.get("path", "")
        if not path_str:
            return ActionResult(success=False, data="Missing 'path' parameter.")

        full_path = self._resolve_path(path_str)
        if not full_path.exists():
            return ActionResult(success=False, data=f"Note not found: {path_str}")

        content = full_path.read_text(encoding="utf-8", errors="ignore")

        # Truncate very long notes for the LLM context
        if len(content) > 5000:
            content = content[:5000] + f"\n\n... (truncated, {len(content)} total characters)"

        return ActionResult(
            success=True,
            data=f"📝 **{path_str}**:\n\n{content}",
        )

    def _create_note(self, params: dict) -> ActionResult:
        path_str = params.get("path", "")
        content = params.get("content", "")

        if not path_str:
            return ActionResult(success=False, data="Missing 'path' parameter.")
        if not content:
            return ActionResult(success=False, data="Missing 'content' parameter.")

        # Ensure .md extension
        if not path_str.endswith(".md"):
            path_str += ".md"

        full_path = self._resolve_path(path_str)

        if full_path.exists():
            return ActionResult(
                success=False,
                data=f"Note already exists: {path_str}. Use 'append_to_note' to add content.",
            )

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Add creation metadata
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        header = f"---\ncreated: {now}\n---\n\n"
        full_path.write_text(header + content, encoding="utf-8")

        return ActionResult(
            success=True,
            data=f"✅ Created note: `{path_str}`",
        )

    def _append_to_note(self, params: dict) -> ActionResult:
        path_str = params.get("path", "")
        content = params.get("content", "")

        if not path_str:
            return ActionResult(success=False, data="Missing 'path' parameter.")
        if not content:
            return ActionResult(success=False, data="Missing 'content' parameter.")

        full_path = self._resolve_path(path_str)
        if not full_path.exists():
            return ActionResult(success=False, data=f"Note not found: {path_str}")

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        append_text = f"\n\n---\n*Appended by Brain on {now}:*\n\n{content}"

        with open(full_path, "a", encoding="utf-8") as f:
            f.write(append_text)

        return ActionResult(
            success=True,
            data=f"✅ Appended to note: `{path_str}`",
        )

    def _list_notes(self, params: dict) -> ActionResult:
        assert self.vault_path is not None
        subdir = params.get("directory", "")
        limit = params.get("limit", 20)

        target = self.vault_path / subdir if subdir else self.vault_path
        if not target.is_dir():
            return ActionResult(success=False, data=f"Directory not found: {subdir}")

        notes = []
        for md_file in sorted(target.rglob("*.md")):
            relative = md_file.relative_to(self.vault_path)
            if any(part.startswith(".") for part in relative.parts):
                continue
            stat = md_file.stat()
            size_kb = stat.st_size / 1024
            notes.append(f"- `{relative}` ({size_kb:.1f} KB)")
            if len(notes) >= limit:
                break

        if not notes:
            return ActionResult(success=True, data=f"No notes found in '{subdir or 'vault root'}'.")

        return ActionResult(
            success=True,
            data=f"Notes in '{subdir or 'vault root'}':\n" + "\n".join(notes),
        )
