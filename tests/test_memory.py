# Copyright (c) 2026 kuro. All Rights Reserved.
"""Tests for the Memory module (SQLite conversation storage)."""

from pathlib import Path
import tempfile

from sugar.core.memory import Memory


class TestMemory:
    """Test conversation memory CRUD operations."""

    def setup_method(self) -> None:
        """Create a temporary database for each test."""
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_memory.db"
        self.memory = Memory(self.db_path)

    def test_create_conversation(self) -> None:
        conv_id = self.memory.new_conversation("Test Chat")
        assert conv_id is not None
        assert len(conv_id) > 0

    def test_add_and_get_messages(self) -> None:
        conv_id = self.memory.new_conversation("Test")
        self.memory.add_message(conv_id, "user", "Hello!")
        self.memory.add_message(conv_id, "assistant", "Hi there!")

        messages = self.memory.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello!"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    def test_get_context_messages(self) -> None:
        conv_id = self.memory.new_conversation("Test")
        self.memory.add_message(conv_id, "user", "What's up?")
        self.memory.add_message(conv_id, "assistant", "Not much!")

        context = self.memory.get_context_messages(conv_id)
        assert len(context) == 2
        assert context[0] == {"role": "user", "content": "What's up?"}
        assert context[1] == {"role": "assistant", "content": "Not much!"}

    def test_list_conversations(self) -> None:
        self.memory.new_conversation("Chat 1")
        self.memory.new_conversation("Chat 2")

        convs = self.memory.list_conversations()
        assert len(convs) == 2

    def test_search_messages(self) -> None:
        conv_id = self.memory.new_conversation("Test")
        self.memory.add_message(conv_id, "user", "Tell me about Linear")
        self.memory.add_message(conv_id, "assistant", "Linear is a project management tool")
        self.memory.add_message(conv_id, "user", "What about Obsidian?")

        results = self.memory.search_messages("Linear")
        assert len(results) == 2  # Both messages contain "Linear"

    def test_message_limit(self) -> None:
        conv_id = self.memory.new_conversation("Test")
        for i in range(30):
            self.memory.add_message(conv_id, "user", f"Message {i}")

        messages = self.memory.get_messages(conv_id, limit=5)
        assert len(messages) == 5
        # Should get the most recent 5
        assert messages[-1].content == "Message 29"

    def test_empty_conversation(self) -> None:
        conv_id = self.memory.new_conversation("Empty")
        messages = self.memory.get_messages(conv_id)
        assert len(messages) == 0
