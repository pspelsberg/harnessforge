"""Authenticated harness catalog, planning and gated advancement API."""
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.features.coding_harness.contracts import AdvanceRequest,HarnessImport
from app.features.coding_harness.service import CodingHarnessError,CodingHarnessService
class PlanRequest(BaseModel):
 model_config=ConfigDict(strict=True,extra="forbid")
 template_id:str=Field(min_length=1,max_length=128);session_id:str=Field(min_length=1,max_length=128);workspace_realpath:str=Field(min_length=1,max_length=4096)
def router_for(service:CodingHarnessService)->APIRouter:
 router=APIRouter()
 @router.get("/api/harness/templates")
 async def templates():return {"templates":[item.model_dump(mode="json") for item in service.templates()]}
 @router.post("/api/harness/templates",status_code=201)
 async def import_template(request:HarnessImport):
  try:return service.import_template(request).model_dump(mode="json")
  except CodingHarnessError as exc:raise HTTPException(status_code=400,detail="harness template rejected") from exc
 @router.post("/api/harness/plans",status_code=201)
 async def plan(request:PlanRequest):
  try:return service.plan(request.template_id,request.session_id,request.workspace_realpath).model_dump(mode="json")
  except CodingHarnessError as exc:raise HTTPException(status_code=400,detail="harness plan rejected") from exc
 @router.post("/api/harness/plans/advance")
 async def advance(request:AdvanceRequest):
  try:plan,report=await service.advance(request);return {"plan":plan.model_dump(mode="json"),"artifact":report.model_dump(mode="json")}
  except CodingHarnessError as exc:raise HTTPException(status_code=409,detail="harness advance rejected") from exc
 return router
