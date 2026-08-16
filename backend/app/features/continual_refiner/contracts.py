"""Redacted trajectory, suggestion and atomic patch contracts."""
from __future__ import annotations
from typing import Any,Literal
import json
from pydantic import ConfigDict,Field,field_validator
from app.core.extension_contracts import ExtensionContract,EXTENSION_POLICY
from app.core.json_values import validate_json_value
from app.core.security.redaction import redact_payload,redact
_ID=r"^[A-Za-z0-9._-]{1,128}$"; _SHA=r"^[0-9a-f]{64}$"
class Trajectory(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 run_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); workspace_realpath:str=Field(min_length=1,max_length=4096); events:list[dict[str,Any]]=Field(default_factory=list,max_length=512)
 @field_validator("events")
 @classmethod
 def safe_events(cls,value):
  clean=redact_payload(value); validate_json_value(clean)
  if len(json.dumps(clean,ensure_ascii=False,separators=(",",":")).encode())>EXTENSION_POLICY.max_context_bytes: raise ValueError("trajectory exceeds limit")
  return clean
class Finding(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 finding_id:str=Field(min_length=1,max_length=128,pattern=_ID); kind:Literal["fact","hypothesis","suggestion"]; title:str=Field(min_length=1,max_length=256); evidence:list[str]=Field(min_length=1,max_length=16); risk:Literal["low","medium","high","critical"]; confidence:float=Field(ge=0,le=1)
 @field_validator("title","evidence")
 @classmethod
 def redact_text(cls,value): return redact_payload(value)
class Patch(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 patch_id:str=Field(min_length=1,max_length=128,pattern=_ID); suggestion_id:str=Field(min_length=1,max_length=128,pattern=_ID); path:str=Field(min_length=1,max_length=256); operation:Literal["replace"]; expected_hash:str=Field(pattern=_SHA); old_text:str=Field(max_length=65536); new_text:str=Field(max_length=65536); diff:str=Field(max_length=131072)
 @field_validator("old_text","new_text","diff")
 @classmethod
 def safe_text(cls,value):
  if "\x00" in value: raise ValueError("patch contains NUL")
  return redact(value,limit=131072)
class Suggestion(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 suggestion_id:str=Field(min_length=1,max_length=128,pattern=_ID); run_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); finding:Finding; patch:Patch; status:Literal["pending","applied","rejected","rolled_back","expired"]="pending"; expires_at:str=Field(min_length=1,max_length=64)
class AnalyzeRequest(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 trajectory:Trajectory
 candidate_patch:Patch|None=None

class AnalyzeResponse(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 run_id:str=Field(min_length=1,max_length=128,pattern=_ID); findings:list[Finding]=Field(max_length=32); suggestions:list[Suggestion]=Field(max_length=32)
class ApplyRequest(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 suggestion_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); request_id:str=Field(min_length=1,max_length=128,pattern=_ID); nonce:str=Field(min_length=32,max_length=64); action_fingerprint:str=Field(pattern=_SHA); run_id:str=Field(min_length=1,max_length=128,pattern=_ID)
class RollbackRequest(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 suggestion_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); expected_hash:str=Field(pattern=_SHA)
