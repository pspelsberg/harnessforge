"""Authenticated REPL session endpoints."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.features.repl_sandbox.contracts import ReplExecuteRequest
from app.features.repl_sandbox.sessions import ReplError, ReplLimitError, ReplSessionManager

def router_for(manager: ReplSessionManager) -> APIRouter:
    router=APIRouter()
    @router.post("/api/repl/sessions", status_code=201)
    async def create_session():
        try: return (await manager.create()).model_dump(mode="json")
        except ReplLimitError as exc: raise HTTPException(status_code=429,detail="REPL session limit exceeded") from exc
        except ReplError as exc: raise HTTPException(status_code=400,detail="REPL session unavailable") from exc

    @router.get("/api/repl/sessions/{session_id}")
    async def info(session_id: str):
        try: return (await manager.info(session_id)).model_dump(mode="json")
        except ReplError as exc: raise HTTPException(status_code=404,detail="REPL session unavailable") from exc

    @router.post("/api/repl/sessions/{session_id}/execute")
    async def execute(session_id: str, request: ReplExecuteRequest):
        try: return (await manager.execute(session_id,request)).model_dump(mode="json")
        except ReplError as exc: raise HTTPException(status_code=404,detail="REPL session unavailable") from exc

    @router.post("/api/repl/sessions/{session_id}/interrupt")
    async def interrupt(session_id: str):
        try: await manager.interrupt(session_id)
        except ReplError as exc: raise HTTPException(status_code=404,detail="REPL session unavailable") from exc
        return {"session_id":session_id,"status":"closed"}

    @router.delete("/api/repl/sessions/{session_id}", status_code=204)
    async def close(session_id: str):
        await manager.close(session_id)
        return None
    return router
