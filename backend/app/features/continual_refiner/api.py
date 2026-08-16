"""Authenticated refiner analysis, review and gated mutation endpoints."""
from __future__ import annotations
from fastapi import APIRouter,HTTPException,Query
from app.features.continual_refiner.contracts import AnalyzeRequest,ApplyRequest,RollbackRequest
from app.features.continual_refiner.service import RefinerError,RefinerService
def router_for(service:RefinerService)->APIRouter:
 router=APIRouter()
 @router.post("/api/refiner/analyze")
 async def analyze(request:AnalyzeRequest):
  try:return (await service.analyze(request)).model_dump(mode="json")
  except RefinerError as exc:raise HTTPException(status_code=400,detail="refiner analysis rejected") from exc
 @router.get("/api/refiner/suggestions")
 async def suggestions(session_id:str=Query(min_length=1,max_length=128),run_id:str|None=None):
  try:return {"suggestions":[item.model_dump(mode="json") for item in await service.list(session_id,run_id)]}
  except RefinerError as exc:raise HTTPException(status_code=400,detail="suggestions unavailable") from exc
 @router.post("/api/refiner/apply")
 async def apply(request:ApplyRequest):
  try:return (await service.apply(request)).model_dump(mode="json")
  except RefinerError as exc:raise HTTPException(status_code=409,detail="refiner apply rejected") from exc
 @router.post("/api/refiner/rollback")
 async def rollback(request:RollbackRequest):
  try:return (await service.rollback(request)).model_dump(mode="json")
  except RefinerError as exc:raise HTTPException(status_code=409,detail="rollback rejected") from exc
 return router
