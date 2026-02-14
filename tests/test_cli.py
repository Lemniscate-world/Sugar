# Copyright (c) 2026 kuro. All Rights Reserved.
"""Tests for the CLI interface."""

from unittest.mock import MagicMock, patch
import pytest
import sys
from io import StringIO

from sugar.interfaces.cli import main, print_banner


class TestCLI:
    """Test suite for the CLI interface using mocks."""

    def test_print_banner(self) -> None:
        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_banner()
            # The banner uses ASCII art, let's check for part of the structure or reset code
            assert "\033[0m" in fake_out.getvalue()
            # Check for the tagline
            assert "Your personal AI operating layer" in fake_out.getvalue()

    @patch("sugar.interfaces.cli.create_engine")
    @patch("builtins.input")
    @patch("sugar.interfaces.cli.print")
    def test_main_loop_quit(self, mock_print: MagicMock, mock_input: MagicMock, mock_create_engine: MagicMock) -> None:
        # Mock engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.llm.is_available.return_value = True
        
        # Simulate typing 'quit' - this should just break the loop and return
        mock_input.side_effect = ["quit"]
        
        main()
        
        mock_engine.start_conversation.assert_called()

    @patch("sugar.interfaces.cli.create_engine")
    @patch("builtins.input")
    def test_main_loop_status_command(self, mock_input: MagicMock, mock_create_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.llm.is_available.return_value = True
        mock_engine.get_status.return_value = {
            "llm_available": True,
            "model": "mistral",
            "active_conversation": "test",
            "connectors": {"web": True}
        }
        
        # Simulate 'status' then 'quit'
        mock_input.side_effect = ["status", "quit"]
        
        with patch("sys.stdout", new=StringIO()) as fake_out:
            main()
            assert "System Status" in fake_out.getvalue()
            assert "Connected" in fake_out.getvalue()

    @patch("sugar.interfaces.cli.create_engine")
    @patch("builtins.input")
    def test_main_chat_flow(self, mock_input: MagicMock, mock_create_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.llm.is_available.return_value = True
        mock_engine.process_message.return_value = "I am a robot."
        
        # Simulate chat then exit
        mock_input.side_effect = ["Hello", "exit"]
        
        with patch("sys.stdout", new=StringIO()) as fake_out:
            main()
            output = fake_out.getvalue()
            assert "I am a robot." in output
            assert "Thinking..." in output

    @patch("sugar.interfaces.cli.create_engine")
    @patch("builtins.input")
    def test_main_new_command(self, mock_input: MagicMock, mock_create_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.llm.is_available.return_value = True
        
        mock_input.side_effect = ["new", "q"]
        
        main()
        
        # Should be called twice: once at start, once for 'new'
        assert mock_engine.start_conversation.call_count == 2
        
    @patch("sugar.interfaces.cli.create_engine")
    @patch("builtins.input")
    def test_keyboard_interrupt(self, mock_input: MagicMock, mock_create_engine: MagicMock) -> None:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.llm.is_available.return_value = True
        
        mock_input.side_effect = KeyboardInterrupt
        
        with pytest.raises(SystemExit):
            main()
