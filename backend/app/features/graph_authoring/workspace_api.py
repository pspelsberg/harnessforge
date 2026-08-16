"""Safe, read-only workspace browser use cases."""
from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError

def router_for(workspace:str|Path)->APIRouter:
    router=APIRouter(); boundary=WorkspaceBoundary(workspace)
    @router.get("/api/workspace/list")
    async def list_workspace():
        files=[]
        for path in sorted(boundary.workspace.rglob("*.md")):
            try: rel=path.relative_to(boundary.workspace); safe=boundary.resolve(rel,must_exist=True)
            except (ValueError,UnsafePathError): continue
            if safe.is_file() and len(rel.parts)<=8 and safe.stat().st_size<=512*1024: files.append(str(rel))
        return {"files":files[:1000]}
    @router.get("/api/workspace/read")
    async def read_workspace(path:str=Query(min_length=1,max_length=4096)):
        try: target=boundary.resolve(path,must_exist=True)
        except UnsafePathError as exc: raise HTTPException(status_code=400,detail="invalid workspace path") from exc
        if not target.is_file() or not target.name.endswith(".md") or target.stat().st_size>512*1024: raise HTTPException(status_code=400,detail="unsupported workspace file")
        try: return {"path":path,"content":target.read_text(encoding="utf-8")}
        except (OSError,UnicodeError) as exc: raise HTTPException(status_code=422,detail="file cannot be read") from exc
    return router
