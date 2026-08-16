"""Retention boundary for the local index (only current version is exposed)."""
from __future__ import annotations
MAX_VERSIONS=2
def retained_versions(current:int)->list[int]:return list(range(max(1,current-MAX_VERSIONS+1),current+1)) if current else []
