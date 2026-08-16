"""Normalized MCP event factory."""
from __future__ import annotations
from typing import Any
from app.core.extension_contracts import ExtensionEvent

def mcp_event(run_id: str,name: str,*,phase: str="progress",error_code: str|None=None,payload: dict[str,Any]|None=None)->ExtensionEvent:
    return ExtensionEvent(namespace="mcp_gateway",name=name,run_id=run_id,phase=phase,error_code=error_code,payload=payload or {})
