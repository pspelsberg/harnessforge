"""Redaction at observability and persistence boundaries."""
import re
from typing import Any

_SECRET = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+|\bbearer\s+|(?:api[_-]?key|token|secret)\s*[:=]\s*)[^\s,;]+")
_SECRET_KEYS={"authorization","cookie","set_cookie","api_key","apikey","access_token","refresh_token","token","secret","password"}

def redact(value: str, *, limit: int = 4096) -> str:
    return _SECRET.sub(lambda m: m.group(1) + "[REDACTED]", value)[:limit]

def redact_payload(value: Any, *, key: str | None = None) -> Any:
    if key and key.casefold().replace("-","_") in _SECRET_KEYS:
        return "[REDACTED]"
    if isinstance(value,str): return redact(value)
    if isinstance(value,list): return [redact_payload(item) for item in value[:128]]
    if isinstance(value,dict): return {str(k):redact_payload(v,key=str(k)) for k,v in list(value.items())[:64]}
    return value
