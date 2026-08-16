"""Coding harness catalog and gated declarative run plans."""
from __future__ import annotations
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.core.extension_ports import HumanApprovalPort,ApprovalPortError
from app.features.coding_harness.catalog import HarnessCatalog,HarnessCatalogError
from app.features.coding_harness.contracts import AdvanceRequest,ArtifactReport,HarnessImport,HarnessTemplate,RunPlan
from app.features.coding_harness.planner import HarnessPlanner,PlannerError
class CodingHarnessError(RuntimeError):pass
class CodingHarnessService:
 def __init__(self,workspace:str|Path,gate_service:HumanApprovalPort):
  try:self.boundary=WorkspaceBoundary(workspace)
  except UnsafePathError as exc:raise CodingHarnessError("invalid harness workspace") from exc
  self.catalog=HarnessCatalog();self.planner=HarnessPlanner();self.gates=gate_service
 def import_template(self,request:HarnessImport)->HarnessTemplate:
  try:template=self.catalog.import_template(request);self.planner.register(template);return template
  except HarnessCatalogError as exc:raise CodingHarnessError("template rejected") from exc
 def templates(self):return self.catalog.list()
 def plan(self,template_id:str,session_id:str,workspace_realpath:str)->RunPlan:
  try:
   resolved=Path(workspace_realpath).resolve(strict=True)
   if resolved!=self.boundary.workspace:raise CodingHarnessError("workspace mismatch")
   return self.planner.create(template_id,session_id,str(resolved))
  except (OSError,RuntimeError,PlannerError) as exc:raise CodingHarnessError("plan rejected") from exc
 async def advance(self,request:AdvanceRequest)->tuple[RunPlan,ArtifactReport]:
  try:plan=self.planner.get(request.plan_id)
  except PlannerError as exc:raise CodingHarnessError("plan unavailable") from exc
  gate_approved=False
  if plan.status=="awaiting_gate":
   if request.gate is None:return self.planner.advance(request,gate_approved=False)
   step=self.catalog.get(plan.template_id).steps[plan.current_step];action=step.action;expected_action=f"harness.{action}";expected_class="git_commit" if action=="git_commit" else "git_push" if action=="git_push" else "tool_write"
   try:gate=await self.gates.consume(request.gate)
   except ApprovalPortError as exc:raise CodingHarnessError("human approval required") from exc
   if gate.gate_class!=expected_class or gate.preview.action!=expected_action or gate.preview.command!=f"plan:{plan.plan_id}:step:{plan.current_step}":raise CodingHarnessError("gate binding mismatch")
   gate_approved=True
  try:return self.planner.advance(request,gate_approved=gate_approved)
  except PlannerError as exc:raise CodingHarnessError("plan advance rejected") from exc
