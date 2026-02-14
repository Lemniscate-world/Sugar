# 🧠 Brain

> Your personal AI operating layer — one chat interface for all your tools.

Brain is a local-first AI assistant that connects your productivity tools (Linear, Obsidian, web) through a single conversational interface powered by [Ollama](https://ollama.com) (free, local LLM).

## Features

- 💬 **Chat with your tools** — "What's the status of project X in Linear?"
- 🔗 **Cross-source reasoning** — "Based on my Obsidian notes, create a Linear issue for..."
- 🏠 **Local-first** — LLM runs on your machine via Ollama. No paid APIs.
- 🔌 **Pluggable connectors** — Easy to add new tools.

## Quick Start

### 1. Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral
```

### 2. Setup Brain
```bash
cd brain/
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env with your API keys and vault path
```

### 4. Run
```bash
# Start Ollama (in another terminal)
ollama serve

# Chat with Brain
python -m brain.interfaces.cli
```

## Connectors

| Connector | Status | API Key Required |
|---|---|---|
| **Obsidian** | ✅ Ready | No (local files) |
| **Linear** | ✅ Ready | Yes (`LINEAR_API_KEY`) |
| **Web Search** | ✅ Ready | No (DuckDuckGo) |
| **Telegram** | 🔜 Planned | Yes (`TELEGRAM_BOT_TOKEN`) |
| **WhatsApp** | 🔜 Planned | Yes (Twilio) |

## Architecture

```
User Message → CLI/Telegram
                   ↓
              Brain Engine
                   ↓
         ┌────────┼────────┐
         ↓        ↓        ↓
      Ollama    Memory   Connectors
      (LLM)    (SQLite)  (Linear, Obsidian, Web)
```

## License

Copyright (c) 2026 kuro. All Rights Reserved. Proprietary license.
