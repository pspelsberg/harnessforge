"""Authenticated checkpoint and fork endpoints."""
from __future__ import annotations
from fastapi import APIRouter,HTTPException,Query
from app.features.time_travel.contracts import CreateCheckpointRequest,ForkRequest
from app.features.time_travel.service import TimeTravelError,TimeTravelService

def router_for(service: TimeTravelService)->APIRouter:
    router=APIRouter()
    @router.post("/api/time-travel/checkpoints",status_code=201)
    async def checkpoint(request: CreateCheckpointRequest):
        try: return (await service.create_checkpoint(request)).model_dump(mode="json")
        except TimeTravelError as exc: raise HTTPException(status_code=400,detail="checkpoint rejected") from exc
    @router.get("/api/time-travel/checkpoints/{checkpoint_id}")
    async def read_checkpoint(checkpoint_id: str,run_id: str=Query(min_length=1,max_length=128),session_id: str=Query(min_length=1,max_length=128),graph_version: str=Query(pattern=r"^[0-9a-f]{64}$"),workspace_realpath: str=Query(min_length=1,max_length=4096)):
        try:
            request=ForkRequest(checkpoint_id=checkpoint_id,run_id=run_id,session_id=session_id,graph_version=graph_version,workspace_realpath=workspace_realpath)
            return (await service.read(request)).model_dump(mode="json")
        except (TimeTravelError,ValueError) as exc: raise HTTPException(status_code=404,detail="checkpoint unavailable") from exc
    @router.post("/api/time-travel/forks",status_code=201)
    async def fork(request: ForkRequest):
        try: return (await service.fork(request)).model_dump(mode="json")
        except TimeTravelError as exc: raise HTTPException(status_code=409,detail="fork rejected") from exc
    return router
