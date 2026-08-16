"""Bounded self-healing plan state machine; it never executes tools."""
from __future__ import annotations
import uuid
from app.core.security.redaction import redact
from app.features.coding_harness.contracts import AdvanceRequest,ArtifactReport,HarnessTemplate,RunPlan
class PlannerError(RuntimeError):pass
class HarnessPlanner:
 def __init__(self):self._plans={};self._templates={}
 def register(self,template:HarnessTemplate):self._templates[template.template_id]=template
 def create(self,template_id:str,session_id:str,workspace:str)->RunPlan:
  if template_id not in self._templates:raise PlannerError("template unavailable")
  t=self._templates[template_id];step=t.steps[0];gate="required" if step.requires_gate or step.action in {"git_commit","git_push"} else "not_required";plan=RunPlan(plan_id="plan-"+uuid.uuid4().hex,template_id=template_id,session_id=session_id,workspace_realpath=workspace,current_step=0,attempt=0,status="awaiting_gate" if gate=="required" else "planned",gate_status=gate);self._plans[plan.plan_id]=plan;return plan
 def get(self,plan_id):
  if plan_id not in self._plans:raise PlannerError("plan unavailable")
  return self._plans[plan_id]
 def _save(self,plan,report):self._plans[plan.plan_id]=plan;return plan,report
 def advance(self,request:AdvanceRequest,*,gate_approved:bool=False):
  plan=self.get(request.plan_id)
  if plan.session_id!=request.session_id:raise PlannerError("plan binding mismatch")
  if plan.status in {"succeeded","failed","cancelled"}:raise PlannerError("plan terminal")
  template=self._templates[plan.template_id];step=template.steps[plan.current_step]
  if plan.status=="awaiting_gate":
   if not gate_approved:return self._save(plan,ArtifactReport(plan_id=plan.plan_id,status="awaiting_gate",diff=plan.diff,report="Human approval required"))
   plan=plan.model_copy(update={"status":"running","gate_status":"approved"})
  output=redact(request.tool_output);diff=redact(request.diff)
  if step.action=="test" and not request.test_passed:
   attempt=plan.attempt+1
   if attempt>=step.max_attempts:
    plan=plan.model_copy(update={"attempt":attempt,"status":"failed","report":output,"diff":diff});return self._save(plan,ArtifactReport(plan_id=plan.plan_id,status="failed",diff=diff,report=output))
   plan=plan.model_copy(update={"attempt":attempt,"status":"running","report":output,"diff":diff});return self._save(plan,ArtifactReport(plan_id=plan.plan_id,status="running",diff=diff,report=f"retry {attempt}/{step.max_attempts}: {output}"))
  next_step=plan.current_step+1
  if next_step>=len(template.steps):
   plan=plan.model_copy(update={"status":"succeeded","report":output,"diff":diff});return self._save(plan,ArtifactReport(plan_id=plan.plan_id,status="succeeded",diff=diff,report=output,published=False))
  next_policy=template.steps[next_step];gate="required" if next_policy.requires_gate or next_policy.action in {"git_commit","git_push"} else "not_required";plan=plan.model_copy(update={"current_step":next_step,"attempt":0,"status":"awaiting_gate" if gate=="required" else "running","gate_status":gate,"report":output,"diff":diff});return self._save(plan,ArtifactReport(plan_id=plan.plan_id,status="awaiting_gate" if gate=="required" else "running",diff=diff,report="Human approval required" if gate=="required" else output))
