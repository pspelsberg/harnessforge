"""Redaction at the observability boundary."""
import re

_SECRET = re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+|(?:api[_-]?key|token|secret)\s*[:=]\s*)[^\s,;]+")

def redact(value: str, *, limit: int = 4096) -> str:
    return _SECRET.sub(lambda m: m.group(1) + "[REDACTED]", value)[:limit]
