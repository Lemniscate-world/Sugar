"""Sugar Setup GUI — FastAPI backend for the setup wizard."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
        result = subprocess.run(
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
    print(f"\n🍬 Sugar Setup Wizard running at: http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
