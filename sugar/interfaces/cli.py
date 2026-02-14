# Copyright (c) 2026 kuro. All Rights Reserved.
"""CLI interface — interactive terminal chat with Sugar."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sugar.config import Config
from sugar.connectors.linear import LinearConnector
from sugar.connectors.obsidian import ObsidianConnector
from sugar.connectors.web import WebConnector
from sugar.core.engine import Engine

# Colors for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner() -> None:
    """Print the Sugar startup banner."""
    print(f"""
{CYAN}{BOLD}
  ███████╗██╗   ██╗ ██████╗  █████╗ ██████╗
  ██╔════╝██║   ██║██╔════╝ ██╔══██╗██╔══██╗
  ███████╗██║   ██║██║  ███╗███████║██████╔╝
  ╚════██║██║   ██║██║   ██║██╔══██║██╔══██╗
  ███████║╚██████╔╝╚██████╔╝██║  ██║██║  ██║
  ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
{RESET}
{DIM}  Your personal AI operating layer{RESET}
{DIM}  Type 'quit' to exit, 'status' for system info{RESET}
""")


def print_status(engine: Engine) -> None:
    """Print the current engine status."""
    status = engine.get_status()
    llm_status = f"{GREEN}✓ Connected{RESET}" if status["llm_available"] else f"{RED}✗ Not available{RESET}"

    print(f"\n{BOLD}System Status:{RESET}")
    print(f"  LLM: {llm_status} (model: {status['model']})")
    print(f"  Conversation: {status['active_conversation'] or 'None'}")
    print(f"  {BOLD}Connectors:{RESET}")

    for name, configured in status["connectors"].items():
        icon = f"{GREEN}✓{RESET}" if configured else f"{YELLOW}○{RESET} (not configured)"
        print(f"    {icon} {name}")
    print()


def create_engine() -> Engine:
    """Create and configure the Sugar engine with all connectors."""
    # Load .env if present
    config = Config()
    config.load_dotenv(Path(".env"))

    engine = Engine(config)

    # Register all connectors
    engine.register_connector(LinearConnector(config.linear_api_key))
    engine.register_connector(ObsidianConnector(config.obsidian_vault_path))
    engine.register_connector(WebConnector())

    return engine


def main() -> None:
    """Main CLI entry point — interactive REPL."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    print_banner()

    engine = create_engine()
    engine.start_conversation("CLI Session")

    # Check LLM availability
    if not engine.llm.is_available():
        print(f"{YELLOW}⚠️  Ollama is not running or model '{engine.config.ollama_model}' not found.{RESET}")
        print(f"{DIM}   Start Ollama: ollama serve{RESET}")
        print(f"{DIM}   Pull model:   ollama pull {engine.config.ollama_model}{RESET}")
        print()

    print_status(engine)
    print(f"{DIM}{'─' * 60}{RESET}\n")

    while True:
        try:
            user_input = input(f"{GREEN}{BOLD}You ❯ {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye! 👋{RESET}")
            sys.exit(0)

        if not user_input:
            continue

        # Special commands
        if user_input.lower() in ("quit", "exit", "q"):
            print(f"{DIM}Goodbye! 👋{RESET}")
            break
        if user_input.lower() == "status":
            print_status(engine)
            continue
        if user_input.lower() == "new":
            engine.start_conversation("CLI Session")
            print(f"{DIM}Started new conversation.{RESET}\n")
            continue

        # Process through Sugar
        print(f"\n{DIM}Thinking...{RESET}")
        response = engine.process_message(user_input)
        print(f"\n{CYAN}{BOLD}Sugar ❯{RESET} {response}\n")


if __name__ == "__main__":
    main()
