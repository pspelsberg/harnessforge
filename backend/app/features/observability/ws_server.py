"""Validated WebSocket command protocol for observability/run control."""
from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Any
from app.core.config import CAPS
class WebSocketProtocolError(ValueError): pass
_ALLOWED={"auth","ping","run.start","run.cancel","run.pause","run.resume"}
@dataclass(frozen=True)
class WebSocketCommand:
    type: str
    payload: dict[str,Any]
    token: str | None = None
    @classmethod
    def parse(cls,message:dict[str,Any])->"WebSocketCommand":
        if not isinstance(message,dict) or not isinstance(message.get("type"),str) or message["type"] not in _ALLOWED: raise WebSocketProtocolError("unknown websocket command")
        if len(json.dumps(message,ensure_ascii=False,separators=(",",":")).encode())>CAPS.max_event_bytes: raise WebSocketProtocolError("websocket command too large")
        payload=message.get("payload",{})
        if not isinstance(payload,dict): raise WebSocketProtocolError("websocket payload must be an object")
        token=message.get("token")
        if token is not None and (not isinstance(token,str) or len(token)>512): raise WebSocketProtocolError("invalid websocket token")
        return cls(message["type"],payload,token)
