"""Authenticated RLM orchestration endpoint factory."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import ConfigDict, Field
from app.core.extension_contracts import ExtensionContract
from app.features.rlm.contracts import AggregateResult, ChildAgentSpec
from app.features.rlm.spawner import RlmSpawner

class RlmRunRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    specs: list[ChildAgentSpec]=Field(min_length=1,max_length=8)
    allowed_bindings: list[str]=Field(default_factory=list,max_length=32)

def router_for(spawner: RlmSpawner)->APIRouter:
    router=APIRouter()
    @router.post("/api/rlm/run")
    async def run(request: RlmRunRequest)->dict:
        result=await spawner.spawn(request.run_id,request.specs,allowed_bindings=set(request.allowed_bindings))
        return result.model_dump(mode="json")
    return router
