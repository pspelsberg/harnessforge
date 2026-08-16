"""Normalized human-gate event factory."""
from __future__ import annotations
from typing import Any
from app.core.extension_contracts import ExtensionEvent

def gate_event(run_id: str,name: str,*,phase: str="progress",error_code: str|None=None,payload: dict[str,Any]|None=None)->ExtensionEvent:
    return ExtensionEvent(namespace="human_gates",name=name,run_id=run_id,phase=phase,error_code=error_code,payload=payload or {})
