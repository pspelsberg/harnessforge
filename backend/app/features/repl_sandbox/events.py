"""Normalized event factory for REPL observers."""
from __future__ import annotations
from typing import Any
from app.core.extension_contracts import ExtensionEvent

def repl_event(session_id: str, name: str, *, phase: str = "progress", error_code: str | None = None, payload: dict[str, Any] | None = None) -> ExtensionEvent:
    return ExtensionEvent(namespace="repl_sandbox",name=name,run_id=session_id,phase=phase,error_code=error_code,payload=payload or {})
