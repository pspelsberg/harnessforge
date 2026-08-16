"""Authenticated graph file use cases."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
from app.features.graph_authoring.contracts import ForgeGraph
from app.features.graph_authoring.validator import validate_graph

class GraphWriteRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    path: str=Field(min_length=1,max_length=4096)
    graph: ForgeGraph

class GraphGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=4096)
    model: str | None = Field(default="qwen2.5-coder:32b", max_length=128)

def router_for(workspace: Path)->APIRouter:
    router=APIRouter()
    boundary=WorkspaceBoundary(workspace)

    @router.post("/api/graph/generate")
    async def generate_graph(request: GraphGenerateRequest):
        from app.features.graph_authoring.generator import generate_graph_from_prompt
        try:
            graph = await generate_graph_from_prompt(request.prompt, request.model or "qwen2.5-coder:32b")
            return graph
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"graph generation failed: {str(exc)}") from exc

    @router.post("/api/graph",status_code=201)
    async def save_graph(request: GraphWriteRequest):
        try:
            target=boundary.resolve(request.path)
            if target.exists() or target.is_symlink(): raise UnsafePathError("destination exists")
            if not target.name.endswith(".forge.json"): raise UnsafePathError("graph file extension required")
            parent=target.parent
            if not parent.is_dir(): raise UnsafePathError("parent directory does not exist")
            validation=validate_graph(request.graph)
            if not validation.valid: raise UnsafePathError("graph validation failed")
            content=request.graph.model_dump_json(indent=2).encode("utf-8")
            fd,tmp=tempfile.mkstemp(prefix=".forge-",suffix=".tmp",dir=parent)
            try:
                with os.fdopen(fd,"wb") as handle: handle.write(content); handle.flush(); os.fsync(handle.fileno())
                os.replace(tmp,target)
            except OSError:
                try: os.unlink(tmp)
                except OSError: pass
                raise
        except (UnsafePathError,OSError) as exc: raise HTTPException(status_code=400,detail="invalid graph path") from exc
        return {"path":str(target.relative_to(boundary.workspace)),"review_only":True}
    @router.get("/api/graph/{path:path}")
    async def load_graph(path: str):
        try: target=boundary.resolve(path,must_exist=True)
        except UnsafePathError as exc: raise HTTPException(status_code=400,detail="invalid graph path") from exc
        if not target.name.endswith(".forge.json"): raise HTTPException(status_code=400,detail="graph file extension required")
        try: return ForgeGraph.model_validate_json(target.read_text(encoding="utf-8"))
        except (OSError,ValueError) as exc: raise HTTPException(status_code=422,detail="invalid graph file") from exc
    return router
