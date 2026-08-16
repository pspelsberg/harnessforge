"""Secure Provider Settings & Encrypted/Bounded Environment Key Manager."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

class ProviderSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    openai_api_key: str | None = Field(default=None, max_length=512)
    openrouter_api_key: str | None = Field(default=None, max_length=512)
    anthropic_api_key: str | None = Field(default=None, max_length=512)
    gemini_api_key: str | None = Field(default=None, max_length=512)
    mistral_api_key: str | None = Field(default=None, max_length=512)
    ollama_url: str | None = Field(default=None, max_length=256)

def _mask_key(key: str | None) -> str | None:
    if not key or len(key) < 6:
        return None
    return f"{key[:4]}...{key[-4:]}"

def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    res: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        res[k.strip()] = v.strip().strip("'\"")
    return res

def _write_env_file(path: Path, entries: dict[str, str]) -> None:
    parent = path.parent
    lines = [f"{k}={v}" for k, v in sorted(entries.items()) if v]
    content = "\n".join(lines) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".env-", suffix=".tmp", dir=parent)
    try:
        os.fchmod(fd, 0o600)  # Restricted read/write for owner only
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

async def _check_ollama_alive(url: str = "http://127.0.0.1:11434") -> bool:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.get(f"{url.rstrip('/')}/api/version")
            return res.status_code == 200
    except Exception:
        return False

def router_for(workspace: Path) -> APIRouter:
    router = APIRouter()
    env_path = workspace / ".env"

    @router.get("/api/settings/providers")
    async def get_provider_settings():
        openai_key = os.environ.get("OPENAI_API_KEY")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        gemini_key = os.environ.get("GEMINI_API_KEY")
        mistral_key = os.environ.get("MISTRAL_API_KEY")
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

        ollama_connected = await _check_ollama_alive(ollama_url)

        return {
            "openai": {"configured": bool(openai_key), "masked": _mask_key(openai_key)},
            "openrouter": {"configured": bool(openrouter_key), "masked": _mask_key(openrouter_key)},
            "anthropic": {"configured": bool(anthropic_key), "masked": _mask_key(anthropic_key)},
            "gemini": {"configured": bool(gemini_key), "masked": _mask_key(gemini_key)},
            "mistral": {"configured": bool(mistral_key), "masked": _mask_key(mistral_key)},
            "ollama": {"connected": ollama_connected, "url": ollama_url},
            "workspace_env_exists": env_path.is_file(),
        }

    @router.post("/api/settings/providers")
    async def update_provider_settings(payload: ProviderSettingsUpdateRequest):
        existing = _parse_env_file(env_path)

        if payload.openai_api_key is not None:
            clean = payload.openai_api_key.strip()
            if clean:
                os.environ["OPENAI_API_KEY"] = clean
                existing["OPENAI_API_KEY"] = clean
            else:
                os.environ.pop("OPENAI_API_KEY", None)
                existing.pop("OPENAI_API_KEY", None)

        if payload.openrouter_api_key is not None:
            clean = payload.openrouter_api_key.strip()
            if clean:
                os.environ["OPENROUTER_API_KEY"] = clean
                existing["OPENROUTER_API_KEY"] = clean
            else:
                os.environ.pop("OPENROUTER_API_KEY", None)
                existing.pop("OPENROUTER_API_KEY", None)

        if payload.anthropic_api_key is not None:
            clean = payload.anthropic_api_key.strip()
            if clean:
                os.environ["ANTHROPIC_API_KEY"] = clean
                existing["ANTHROPIC_API_KEY"] = clean
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)
                existing.pop("ANTHROPIC_API_KEY", None)

        if payload.gemini_api_key is not None:
            clean = payload.gemini_api_key.strip()
            if clean:
                os.environ["GEMINI_API_KEY"] = clean
                existing["GEMINI_API_KEY"] = clean
            else:
                os.environ.pop("GEMINI_API_KEY", None)
                existing.pop("GEMINI_API_KEY", None)

        if payload.mistral_api_key is not None:
            clean = payload.mistral_api_key.strip()
            if clean:
                os.environ["MISTRAL_API_KEY"] = clean
                existing["MISTRAL_API_KEY"] = clean
            else:
                os.environ.pop("MISTRAL_API_KEY", None)
                existing.pop("MISTRAL_API_KEY", None)

        if payload.ollama_url is not None:
            clean = payload.ollama_url.strip()
            if clean:
                if not re.match(r"^https?://(127\.0\.0\.1|localhost)(:[0-9]+)?", clean):
                    raise HTTPException(status_code=400, detail="Ollama URL must point to localhost (e.g. http://127.0.0.1:11434)")
                os.environ["OLLAMA_BASE_URL"] = clean
                existing["OLLAMA_BASE_URL"] = clean

        try:
            _write_env_file(env_path, existing)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="failed to save .env file") from exc

        return await get_provider_settings()

    return router
