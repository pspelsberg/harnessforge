"""Workspace-bounded local prompt loader with content fingerprints."""
from __future__ import annotations
import hashlib
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
class PromptLoadError(ValueError): pass
class PromptLoader:
    def __init__(self,workspace:str|Path,max_bytes:int=128*1024):
        self.boundary=WorkspaceBoundary(workspace); self.max_bytes=max_bytes
        if not 1<=max_bytes<=1024*1024: raise ValueError("invalid prompt limit")
    def _path(self,relative:str)->Path:
        try: path=self.boundary.resolve(relative,must_exist=True)
        except UnsafePathError as exc: raise PromptLoadError("invalid prompt path") from exc
        if not path.is_file() or path.suffix.casefold() not in {".md",".txt"}: raise PromptLoadError("unsupported prompt file")
        if path.stat().st_size>self.max_bytes: raise PromptLoadError("prompt is too large")
        return path
    def load(self,relative:str)->str:
        path=self._path(relative)
        try: return path.read_text(encoding="utf-8")
        except (OSError,UnicodeError) as exc: raise PromptLoadError("prompt cannot be read") from exc
    def fingerprint(self,relative:str)->str:
        path=self._path(relative)
        try: return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc: raise PromptLoadError("prompt cannot be fingerprinted") from exc
