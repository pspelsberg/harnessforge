"""Explainable suggestion projection; provider/trajectory text remains untrusted."""
from __future__ import annotations
import uuid
from app.features.continual_refiner.contracts import Finding,Patch,Suggestion,Trajectory
from datetime import datetime,timedelta,timezone
class Proposer:
 def propose(self,trajectory:Trajectory,finding:Finding,patch:Patch)->Suggestion:
  suggestion_id="suggestion-"+uuid.uuid4().hex
  bound_patch=patch.model_copy(update={"suggestion_id":suggestion_id})
  return Suggestion(suggestion_id=suggestion_id,run_id=trajectory.run_id,session_id=trajectory.session_id,finding=finding,patch=bound_patch,status="pending",expires_at=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat())
