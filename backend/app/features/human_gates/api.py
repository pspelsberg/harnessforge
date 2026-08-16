"""Authenticated human-gate lifecycle endpoints."""
from __future__ import annotations
from fastapi import APIRouter,HTTPException,Query
from app.features.human_gates.contracts import GateCreateRequest,GateDecision,GateConsumeRequest
from app.features.human_gates.service import HumanGateError,HumanGateService

def router_for(service: HumanGateService)->APIRouter:
    router=APIRouter()
    @router.post("/api/gates",status_code=201)
    async def create(request: GateCreateRequest):
        try: return (await service.create(request)).model_dump(mode="json")
        except HumanGateError as exc: raise HTTPException(status_code=400,detail="gate creation rejected") from exc
    @router.get("/api/gates/{request_id}")
    async def get(request_id: str,session_id: str=Query(min_length=1,max_length=128)):
        try: return (await service.get(request_id,session_id)).model_dump(mode="json")
        except HumanGateError as exc: raise HTTPException(status_code=404,detail="gate unavailable") from exc
    @router.post("/api/gates/{request_id}/decision")
    async def decide(request_id: str,decision: GateDecision):
        if decision.request_id!=request_id: raise HTTPException(status_code=400,detail="gate binding mismatch")
        try: return (await service.decide(decision)).model_dump(mode="json")
        except HumanGateError as exc: raise HTTPException(status_code=409,detail="gate decision rejected") from exc
    @router.post("/api/gates/{request_id}/consume")
    async def consume(request_id: str,request: GateConsumeRequest):
        if request.request_id!=request_id: raise HTTPException(status_code=400,detail="gate binding mismatch")
        try: return (await service.consume(request)).model_dump(mode="json")
        except HumanGateError as exc: raise HTTPException(status_code=409,detail="gate consumption rejected") from exc
    @router.post("/api/gates/runs/{run_id}/cancel")
    async def cancel(run_id: str): return {"cancelled":await service.cancel_run(run_id)}
    return router
