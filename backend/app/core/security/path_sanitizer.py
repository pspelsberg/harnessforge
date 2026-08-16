"""Workspace path policy used by all local file features."""
from __future__ import annotations

import ntpath
from dataclasses import dataclass, field
from pathlib import Path

class UnsafePathError(ValueError):
    """Raised when a path escapes or targets a protected filesystem location."""

@dataclass(frozen=True)
class PathPolicy:
    sensitive_names: frozenset[str] = field(default_factory=lambda: frozenset({".env", ".git", ".ssh"}))
    blocked_roots: tuple[Path, ...] = (Path("/etc"), Path("/usr"), Path("/proc"), Path("/sys"), Path("/dev"))

class WorkspaceBoundary:
    def __init__(self, workspace: str | Path, *, policy: PathPolicy | None = None) -> None:
        self.policy = policy or PathPolicy()
        try: self.workspace = Path(workspace).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc: raise UnsafePathError("workspace is unavailable") from exc
        if not self.workspace.is_dir(): raise UnsafePathError("workspace must be a directory")
        if any(self._inside(self.workspace, blocked) for blocked in self.policy.blocked_roots): raise UnsafePathError("system directory cannot be a workspace")

    def resolve(self, candidate: str | Path, *, must_exist: bool = False) -> Path:
        if not isinstance(candidate, (str, Path)):
            raise UnsafePathError("path must be text")
        raw = str(candidate)
        if not raw or "\x00" in raw or "\\" in raw or ntpath.isabs(raw) or Path(raw).is_absolute():
            raise UnsafePathError("absolute, malformed, or cross-platform paths are forbidden")
        lexical_parts = Path(raw).parts
        if any(part == ".." for part in lexical_parts):
            raise UnsafePathError("path traversal is forbidden")
        if any(self._is_sensitive(part) for part in lexical_parts):
            raise UnsafePathError("sensitive paths are forbidden")
        try: target = (self.workspace / Path(raw)).resolve(strict=must_exist)
        except (OSError, RuntimeError) as exc: raise UnsafePathError("path is unavailable") from exc
        if not self._inside(target, self.workspace):
            raise UnsafePathError("path escapes workspace")
        if any(self._is_sensitive(part) for part in target.relative_to(self.workspace).parts):
            raise UnsafePathError("sensitive paths are forbidden")
        if any(self._inside(target, blocked) for blocked in self.policy.blocked_roots):
            raise UnsafePathError("system paths are forbidden")
        if must_exist and not target.exists():
            raise UnsafePathError("path does not exist")
        return target

    @staticmethod
    def _inside(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def _is_sensitive(self, part: str) -> bool:
        lowered = part.casefold()
        return lowered in {name.casefold() for name in self.policy.sensitive_names} or lowered.startswith(".env.")
