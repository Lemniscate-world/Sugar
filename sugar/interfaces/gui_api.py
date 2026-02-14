"""Sugar Setup GUI — FastAPI backend for the setup wizard."""

from __future__ import annotations

import logging
import os
import subprocess  # nosec
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import ollama
import json
from sugar.config import Config
from sugar.core.engine import Engine
from sugar.connectors.obsidian import ObsidianConnector
from sugar.connectors.linear import LinearConnector
from sugar.connectors.web import WebConnector

logger = logging.getLogger(__name__)

app = FastAPI(title="Sugar Setup", version="0.1.0")

# Allow GUI dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Initialize Engine
config = Config()
# Load env explicitly
config.load_dotenv(PROJECT_ROOT / ".env")
engine = Engine(config)

# Register Connectors
if config.obsidian_enabled:
    engine.register_connector(ObsidianConnector(config.obsidian_vault_path))

if config.linear_enabled:
    engine.register_connector(LinearConnector(config.linear_api_key))

# Always enable Web Search
engine.register_connector(WebConnector())


# --- Models ---


class ConfigUpdate(BaseModel):
    ollama_model: str = "mistral"
    ollama_host: str = "http://localhost:11434"
    linear_api_key: str = ""
    obsidian_vault_path: str = ""
    telegram_bot_token: str = ""


class PathRequest(BaseModel):
    path: str


# --- Routes ---


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "project": "sugar"}


@app.get("/api/status")
def get_status() -> dict:
    """Get the current system status."""
    ollama_running = _check_ollama()
    ollama_models = _list_ollama_models() if ollama_running else []
    env_exists = (PROJECT_ROOT / ".env").exists()

    # Read current config
    current_config = {}
    if env_exists:
        current_config = _read_env()

    return {
        "ollama": {
            "installed": _is_ollama_installed(),
            "running": ollama_running,
            "models": ollama_models,
        },
        "env_exists": env_exists,
        "current_config": current_config,
        "obsidian_vault_valid": _validate_vault(
            current_config.get("OBSIDIAN_VAULT_PATH", "")
        ),
        "linear_configured": bool(current_config.get("LINEAR_API_KEY", "")),
        "engine": engine.get_status(),
    }


@app.post("/api/config/save")
def save_config(config: ConfigUpdate) -> dict:
    """Save configuration to .env file."""
    env_path = PROJECT_ROOT / ".env"
    lines = [
        f"OLLAMA_MODEL={config.ollama_model}",
        f"OLLAMA_HOST={config.ollama_host}",
        f"LINEAR_API_KEY={config.linear_api_key}",
        f"OBSIDIAN_VAULT_PATH={config.obsidian_vault_path}",
        f"TELEGRAM_BOT_TOKEN={config.telegram_bot_token}",
    ]
    env_path.write_text("\n".join(lines) + "\n")
    logger.info("Config saved to %s", env_path)
    return {"success": True, "path": str(env_path)}


@app.post("/api/validate/vault")
def validate_vault(req: PathRequest) -> dict:
    """Validate an Obsidian vault path."""
    path = Path(req.path).expanduser().resolve()
    is_valid = path.is_dir()
    md_count = 0
    has_obsidian = False

    if is_valid:
        md_count = len(list(path.rglob("*.md")))
        has_obsidian = (path / ".obsidian").is_dir()

    return {
        "valid": is_valid,
        "path": str(path),
        "md_count": md_count,
        "is_obsidian_vault": has_obsidian,
    }


@app.post("/api/validate/linear")
def validate_linear(req: PathRequest) -> dict:
    """Validate a Linear API key by making a test query."""
    import requests as http_requests

    api_key = req.path  # Reusing PathRequest for the key
    if not api_key:
        return {"valid": False, "error": "No API key provided"}

    try:
        response = http_requests.post(
            "https://api.linear.app/graphql",
            json={"query": "query { viewer { id name email } }"},
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = response.json()
        if "errors" in data:
            return {"valid": False, "error": data["errors"][0].get("message", "Invalid key")}

        viewer = data.get("data", {}).get("viewer", {})
        return {
            "valid": True,
            "user": viewer.get("name", ""),
            "email": viewer.get("email", ""),
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post("/api/browse")
def browse_directory(req: PathRequest) -> dict:
    """Browse filesystem directories for vault selection."""
    path = Path(req.path).expanduser().resolve()
    if not path.is_dir():
        parent = path.parent
        if parent.is_dir():
            path = parent
        else:
            path = Path.home()

    entries = []
    try:
        for entry in sorted(path.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                entries.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "directory",
                })
            elif entry.suffix == ".md":
                entries.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "file",
                })
    except PermissionError:
        pass

    return {
        "current": str(path),
        "parent": str(path.parent) if path != path.parent else None,
        "entries": entries[:50],
    }


@app.get("/api/ollama/models")
def ollama_models() -> dict:
    """List available Ollama models."""
    return {
        "installed": _is_ollama_installed(),
        "running": _check_ollama(),
        "models": _list_ollama_models(),
    }


# --- Chat & Intelligence APIs ---

@app.post("/api/chat")
def chat(request: Request):
    """Chat with the AI model (streaming)."""
    # Use sync def so FastAPI runs it in threadpool
    import asyncio
    
    # We need to read body in sync endpoint? request.json() is async.
    # Better to use async def and run blocking code in executor, or use Pydantic model.
    # Let's use Pydantic model for body.
    return StreamingResponse(content="Error: use /api/chat/json", status_code=400)

class ChatRequest(BaseModel):
    messages: list[dict]
    model: str = "mistral"
    conversation_id: str | None = None

@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    # active conversation
    cid = req.conversation_id
    
    # extract user message
    user_content = ""
    if req.messages and req.messages[-1]["role"] == "user":
        user_content = req.messages[-1]["content"]

    # Use Engine to manage conversation
    if not cid:
        title = user_content[:40] if user_content else "New Chat"
        cid = engine.start_conversation(title=title)
    else:
        engine.current_conversation = cid

    def event_generator():
        # Send ID first so frontend knows
        yield f"data: {json.dumps({'conversation_id': cid})}\n\n"
        
        # Use Engine's stream processing
        try:
            stream = engine.process_message_stream(user_content)
            for chunk in stream:
                # Engine streams raw text (including tool status)
                # We wrap it in JSON for the frontend
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Chat Stream Error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/conversations")
def list_conversations() -> dict:
    """List recent conversations."""
    return {"conversations": engine.memory.list_conversations(limit=50)}

@app.get("/api/conversations/{cid}")
def get_conversation(cid: str) -> dict:
    """Get messages for a conversation."""
    msgs = engine.memory.get_messages(cid, limit=100)
    return {"messages": [m.to_dict() for m in msgs]}

@app.post("/api/conversations")
def new_conversation() -> dict:
    """Create a new conversation."""
    cid = engine.memory.new_conversation(title="New Chat")
    return {"id": cid, "title": "New Chat"}


class PullRequest(BaseModel):
    name: str

@app.post("/api/models/pull")
def pull_model(req: PullRequest) -> StreamingResponse:
    """Pull a model from Ollama library."""
    def pull_generator():
        try:
            # ollama.pull streams progress objects
            stream = ollama.pull(req.name, stream=True)
            for progress in stream:
                # Convert to dict if needed
                data = progress
                if hasattr(progress, "model_dump"):
                    data = progress.model_dump()
                elif hasattr(progress, "dict"):
                    data = progress.dict()
                
                yield f"data: {json.dumps(data)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(pull_generator(), media_type="text/event-stream")


# --- Serve built GUI ---

GUI_DIST = PROJECT_ROOT / "gui" / "dist"
if GUI_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(GUI_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        """Serve the SPA for all non-API routes."""
        file_path = GUI_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(GUI_DIST / "index.html"))


# --- Helpers ---


def _is_ollama_installed() -> bool:
    try:
        result = subprocess.run(  # nosec
            ["which", "ollama"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_ollama() -> bool:
    try:
        import requests as http_requests
        r = http_requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _list_ollama_models() -> list[str]:
    try:
        import requests as http_requests
        r = http_requests.get("http://localhost:11434/api/tags", timeout=3)
        data = r.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _read_env() -> dict:
    env_path = PROJECT_ROOT / ".env"
    result = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                # Mask sensitive values
                if "KEY" in key or "TOKEN" in key:
                    result[key.strip()] = "••••" + value.strip()[-4:] if len(value.strip()) > 4 else ""
                else:
                    result[key.strip()] = value.strip()
    return result


def _validate_vault(path_str: str) -> bool:
    if not path_str:
        return False
    path = Path(path_str).expanduser()
    return path.is_dir()


def start_server(port: int = 8000) -> None:
    """Start the setup GUI server."""
    import uvicorn
    logger.info("Sugar Setup Wizard running at: http://localhost:%s", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
