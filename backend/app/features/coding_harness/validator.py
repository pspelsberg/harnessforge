"""Hash/signature and capability validation for declarative templates."""
from __future__ import annotations
import hashlib,json
from app.features.coding_harness.contracts import HarnessImport,HarnessTemplate
class HarnessValidationError(ValueError):pass
class HarnessValidator:
 def validate(self,request:HarnessImport)->HarnessTemplate:
  template=request.template; payload=template.model_dump(mode="json");payload.pop("content_hash");payload.pop("signature");digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
  if digest!=template.content_hash or template.signature!=f"local:{digest}":raise HarnessValidationError("template hash/signature invalid")
  available=set(template.capabilities)
  for step in template.steps:
   if step.action=="git_push":
    if not request.enable_push:raise HarnessValidationError("git push is disabled")
    if not step.requires_gate:raise HarnessValidationError("git push requires HITL gate")
   if step.action=="git_commit" and not step.requires_gate:raise HarnessValidationError("git commit requires HITL gate")
   required={"inspect":{"workspace_read"},"edit":{"workspace_write"},"test":{"tests"},"git_commit":{"git_commit"},"git_push":{"git_push"}}[step.action]
   if not required.issubset(available) or not required.issubset(set(step.capabilities)):raise HarnessValidationError("step capability exceeds template")
  return template
