"""Explainable refiner lifecycle; filesystem mutations require a consumed HITL gate."""
from __future__ import annotations
import asyncio,hashlib,os,tempfile,json
from datetime import datetime,timezone
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.human_gates.contracts import GateConsumeRequest
from app.core.extension_ports import HumanApprovalPort,ApprovalPortError
from app.features.continual_refiner.analyzer import Analyzer
from app.features.continual_refiner.contracts import AnalyzeRequest,AnalyzeResponse,ApplyRequest,Finding,Patch,RollbackRequest,Suggestion,Trajectory
from app.features.continual_refiner.patch_policy import PatchPolicy,PatchPolicyError
from app.features.continual_refiner.proposer import Proposer
from app.features.continual_refiner.review_store import ReviewStore,ReviewStoreError
class RefinerError(RuntimeError): pass
class _DeniedApprovalPort:
 async def consume(self,request): raise ApprovalPortError("approval port is not configured")
class RefinerService:
 def __init__(self,workspace: str|Path,gate_service:HumanApprovalPort|None=None):
  try:self.boundary=WorkspaceBoundary(workspace)
  except UnsafePathError as exc:raise RefinerError("invalid refiner workspace") from exc
  self.store=ReviewStore(self.boundary.workspace); self.policy=PatchPolicy(self.boundary); self.analyzer=Analyzer(); self.proposer=Proposer(); self.gates=gate_service or _DeniedApprovalPort(); self._lock=asyncio.Lock()
 def _workspace(self,value:str):
  try: resolved=Path(value).resolve(strict=True)
  except (OSError,RuntimeError) as exc:raise RefinerError("invalid trajectory workspace") from exc
  if resolved!=self.boundary.workspace:raise RefinerError("workspace mismatch")
  return str(resolved)
 async def analyze(self,request:AnalyzeRequest)->AnalyzeResponse:
  self._workspace(request.trajectory.workspace_realpath); findings=self.analyzer.analyze(request.trajectory); suggestions=[]
  if request.candidate_patch and findings:
   try:self.policy.validate(request.candidate_patch)
   except PatchPolicyError as exc:raise RefinerError("candidate patch rejected") from exc
   suggestion=self.proposer.propose(request.trajectory,findings[0],request.candidate_patch); await self.store.save(suggestion); suggestions.append(suggestion)
  return AnalyzeResponse(run_id=request.trajectory.run_id,findings=findings,suggestions=suggestions)
 async def list(self,session_id:str,run_id:str|None=None): return await self.store.list(session_id,run_id)
 async def reject(self,suggestion_id:str,session_id:str)->Suggestion:
  try: return await self.store.transition(suggestion_id,session_id,"pending","rejected")
  except ReviewStoreError as exc: raise RefinerError("suggestion rejection rejected") from exc
 async def apply(self,request:ApplyRequest)->Suggestion:
  async with self._lock:
   try:suggestion=await self.store.get(request.suggestion_id)
   except ReviewStoreError as exc:raise RefinerError("suggestion unavailable") from exc
   if suggestion.session_id!=request.session_id or suggestion.run_id!=request.run_id or suggestion.status!="pending":raise RefinerError("suggestion state rejected")
   try: expires=datetime.fromisoformat(suggestion.expires_at.replace("Z","+00:00")); expired=datetime.now(timezone.utc)>=expires
   except ValueError: expired=True
   if expired: raise RefinerError("suggestion expired")
   try: gate=await self.gates.consume(GateConsumeRequest(request_id=request.request_id,nonce=request.nonce,session_id=request.session_id,run_id=request.run_id,action_fingerprint=request.action_fingerprint))
   except ApprovalPortError as exc:raise RefinerError("human approval required") from exc
   patch_binding=hashlib.sha256(json.dumps({"path":suggestion.patch.path,"expected_hash":suggestion.patch.expected_hash,"old_text":suggestion.patch.old_text,"new_text":suggestion.patch.new_text},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
   if gate.gate_class!="tool_write" or gate.preview.action!="refiner.apply" or gate.preview.command!=f"refiner:{suggestion.suggestion_id}:{patch_binding}" or gate.preview.diff!=suggestion.patch.diff or suggestion.patch.path not in gate.preview.write_targets: raise RefinerError("wrong approval binding")
   try: self.policy.validate(suggestion.patch); target=self.policy.path(suggestion.patch.path); current=target.read_text(encoding="utf-8")
   except (OSError,UnicodeError,PatchPolicyError) as exc:raise RefinerError("patch cannot be applied") from exc
   if hashlib.sha256(current.encode()).hexdigest()!=suggestion.patch.expected_hash or current!=suggestion.patch.old_text:raise RefinerError("patch base changed")
   backup=self.boundary.resolve(f".harnessforge/refiner-backups/{suggestion.suggestion_id}.bak",must_exist=False); backup.parent.mkdir(parents=True,exist_ok=True); backup.write_text(current,encoding="utf-8"); os.chmod(backup,0o600)
   try:self._atomic_write(target,suggestion.patch.new_text); result=await self.store.transition(suggestion.suggestion_id,request.session_id,"pending","applied",str(backup))
   except (OSError,ReviewStoreError) as exc:
    try:self._atomic_write(target,current)
    except OSError: pass
    raise RefinerError("patch transaction failed") from exc
   return result
 def _atomic_write(self,target:Path,text:str):
  fd,tmp=tempfile.mkstemp(prefix=f".{target.name}.",dir=str(target.parent),text=True)
  try:
   with os.fdopen(fd,"w",encoding="utf-8") as handle: handle.write(text); handle.flush(); os.fsync(handle.fileno())
   os.replace(tmp,target)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 async def rollback(self,request:RollbackRequest)->Suggestion:
  async with self._lock:
   try:suggestion=await self.store.get(request.suggestion_id); backup_path=await self.store.backup_path(request.suggestion_id,request.session_id)
   except ReviewStoreError as exc:raise RefinerError("rollback unavailable") from exc
   if suggestion.session_id!=request.session_id or suggestion.status!="applied" or not backup_path:raise RefinerError("rollback state rejected")
   expected_backup=self.boundary.resolve(f".harnessforge/refiner-backups/{suggestion.suggestion_id}.bak",must_exist=False)
   try:
    if Path(backup_path).resolve()!=expected_backup: raise RefinerError("rollback backup binding mismatch")
    target=self.policy.path(suggestion.patch.path); current=target.read_text(encoding="utf-8"); backup=expected_backup.read_text(encoding="utf-8")
   except (OSError,UnicodeError,PatchPolicyError) as exc:raise RefinerError("rollback files unavailable") from exc
   if hashlib.sha256(current.encode()).hexdigest()!=request.expected_hash:raise RefinerError("rollback race detected")
   self._atomic_write(target,backup)
   try:return await self.store.transition(request.suggestion_id,request.session_id,"applied","rolled_back",backup_path)
   except ReviewStoreError as exc:
    try:self._atomic_write(target,current)
    except OSError: pass
    raise RefinerError("rollback transaction failed") from exc
