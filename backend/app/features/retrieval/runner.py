"""Read-only retrieval result normalization independent of LanceDB internals."""
from __future__ import annotations
from typing import Any
from math import isfinite
from app.core.config import CAPS
from app.core.json_values import validate_json_value
from app.features.retrieval.context import UntrustedContext
class RetrievalError(ValueError): pass

def normalize_results(rows: list[dict[str, Any]], *, top_k: int = 5, max_chunk_bytes: int = 16 * 1024) -> list[dict[str, Any]]:
    if not 1 <= top_k <= 20: raise RetrievalError("top_k must be between 1 and 20")
    if not 1 <= max_chunk_bytes <= CAPS.max_event_bytes: raise RetrievalError("invalid chunk limit")
    result=[]
    for row in rows[:top_k]:
        if not isinstance(row,dict) or "text" not in row: raise RetrievalError("retrieval row has no text")
        text=str(row["text"])
        encoded=text.encode("utf-8")
        if len(encoded)>max_chunk_bytes: text=encoded[:max_chunk_bytes].decode("utf-8","ignore")
        raw_score=row.get("score", row.get("_distance", 0.0))
        try: score=float(raw_score)
        except (TypeError,ValueError): score=0.0
        if not isfinite(score): raise RetrievalError("retrieval score must be finite")
        metadata={str(k):v for k,v in row.items() if k not in {"text","score","_distance","vector"}}
        try:
            validate_json_value(metadata)
        except ValueError as exc:
            raise RetrievalError("retrieval metadata is not JSON-safe") from exc
        if len(str(metadata).encode("utf-8")) > max_chunk_bytes: raise RetrievalError("retrieval metadata too large")
        result.append({"text":text,"score":score,"metadata":metadata})
    return result

def as_untrusted(rows: list[dict[str, Any]], **limits: Any) -> list[UntrustedContext]:
    return [UntrustedContext(**item) for item in normalize_results(rows, **limits)]
