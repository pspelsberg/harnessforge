"""Immutable lineage and state fingerprints."""
from __future__ import annotations
import hashlib,json
from typing import Any
def state_hash(state: dict[str,Any])->str: return hashlib.sha256(json.dumps(state,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
