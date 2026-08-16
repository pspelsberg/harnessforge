"""Allowlist and bounded atomic patch policy."""
from __future__ import annotations
import hashlib
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.continual_refiner.contracts import Patch
class PatchPolicyError(ValueError): pass
class PatchPolicy:
 def __init__(self,boundary:WorkspaceBoundary): self.boundary=boundary
 def path(self,raw:str):
  try: target=self.boundary.resolve(raw,must_exist=False)
  except UnsafePathError as exc: raise PatchPolicyError("patch path rejected") from exc
  allowed=raw in {"agents.md","AGENTS.md"} or (raw.startswith("prompts/") and raw.endswith(".md") and raw.count("/")==1)
  if not allowed: raise PatchPolicyError("patch file is not allowlisted")
  return target
 def validate(self,patch:Patch):
  self.path(patch.path)
  if hashlib.sha256(patch.old_text.encode()).hexdigest()!=patch.expected_hash: raise PatchPolicyError("patch base hash mismatch")
  if patch.old_text==patch.new_text or patch.new_text.count("\n")>2048: raise PatchPolicyError("patch has no bounded change")
  return patch
