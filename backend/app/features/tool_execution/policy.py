"""Declarative Local Trust Mode write policy."""
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
from .runner import ToolError

def validate_write_target(boundary:WorkspaceBoundary, relative_target:str, allowed_dirs:list[str])->Path:
    try:
        target=boundary.resolve(relative_target,must_exist=False)
    except UnsafePathError as exc:
        raise ToolError("write target is outside workspace") from exc
    for directory in allowed_dirs:
        try:
            root=boundary.resolve(directory,must_exist=True)
        except UnsafePathError as exc:
            raise ToolError("write directory is outside workspace") from exc
        if target==root or boundary._inside(target,root):
            return target
    raise ToolError("write target is not declared")
