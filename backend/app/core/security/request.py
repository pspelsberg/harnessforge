"""Canonical localhost request validation helpers."""
from __future__ import annotations
_ALLOWED_HOSTS={"127.0.0.1","localhost"}; _ALLOWED_PORTS={None,80,443,5173,8000}; _ALLOWED_ORIGINS={"http://127.0.0.1:5173","http://localhost:5173"}
def valid_host(raw:str)->bool:
    try: host,port=raw.rsplit(":",1) if ":" in raw else (raw,None)
    except ValueError: return False
    return host.casefold() in _ALLOWED_HOSTS and (port is None or (port.isdigit() and int(port) in _ALLOWED_PORTS))
def valid_origin(origin:str|None)->bool: return origin is None or origin in _ALLOWED_ORIGINS
