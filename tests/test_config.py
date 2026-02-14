# Copyright (c) 2026 kuro. All Rights Reserved.
"""Tests for the Config module."""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from sugar.config import Config


class TestConfig:
    """Test suite for configuration management."""

    def test_default_config(self) -> None:
        # Clear env to test defaults
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.ollama_model == "tinyllama:latest"
            assert config.ollama_host == "http://localhost:11434"
            assert config.linear_api_key == ""
            assert config.obsidian_vault_path is None

    def test_env_override(self) -> None:
        env_vars = {
            "OLLAMA_MODEL": "llama3",
            "OLLAMA_HOST": "http://ollama-server:11434",
            "LINEAR_API_KEY": "lin_123",
            "OBSIDIAN_VAULT_PATH": "/tmp/vault"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            assert config.ollama_model == "llama3"
            assert config.ollama_host == "http://ollama-server:11434"
            assert config.linear_api_key == "lin_123"
            # Note: __post_init__ resolves path
            assert str(config.obsidian_vault_path).endswith("vault")

    def test_load_dotenv_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("OLLAMA_MODEL=tinyllama\nLINEAR_API_KEY=key_abc\n")
        
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            config.load_dotenv(env_file)
            assert config.ollama_model == "tinyllama"
            assert config.linear_api_key == "key_abc"

    def test_enabled_properties(self) -> None:
        config = Config()
        
        # Linear
        config.linear_api_key = ""
        assert config.linear_enabled is False
        config.linear_api_key = "abc"
        assert config.linear_enabled is True
        
        # Obsidian
        config.obsidian_vault_path = None
        assert config.obsidian_enabled is False
        # Use a real dir for the property check
        config.obsidian_vault_path = Path("/tmp")
        assert config.obsidian_enabled is True

    def test_system_prompt_default(self) -> None:
        config = Config()
        assert "You are Brain" in config.system_prompt
        assert "Linear" in config.system_prompt
