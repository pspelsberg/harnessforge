"""Authenticated index status, lifecycle and read-only retrieval endpoints."""
from fastapi import APIRouter,HTTPException
from app.features.workspace_indexer.contracts import IndexQuery
from app.features.workspace_indexer.service import IndexerError,WorkspaceIndexService
def router_for(service:WorkspaceIndexService)->APIRouter:
 router=APIRouter()
 @router.get("/api/index/status")
 async def status():return (await service.status()).model_dump(mode="json")
 @router.post("/api/index/rebuild",status_code=202)
 async def rebuild(session_id:str,workspace_realpath:str):
  try:return (await service.rebuild(session_id,workspace_realpath)).model_dump(mode="json")
  except IndexerError as exc:raise HTTPException(status_code=409,detail="index rebuild rejected") from exc
 @router.post("/api/index/pause")
 async def pause():await service.pause();return (await service.status()).model_dump(mode="json")
 @router.post("/api/index/resume")
 async def resume():await service.resume();return (await service.status()).model_dump(mode="json")
 @router.post("/api/index/query")
 async def query(request:IndexQuery):
  try:return (await service.query(request)).model_dump(mode="json")
  except IndexerError as exc:raise HTTPException(status_code=400,detail="index query rejected") from exc
 return router
