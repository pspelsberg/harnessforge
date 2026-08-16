"""Strict signed-template, step-policy and run-plan contracts."""
from __future__ import annotations
from typing import Literal
import json
from pydantic import ConfigDict,Field,field_validator
from app.core.extension_contracts import ExtensionContract,EXTENSION_POLICY
from app.core.security.redaction import redact
from app.features.human_gates.contracts import GateConsumeRequest
_ID=r"^[A-Za-z0-9._-]{1,128}$";_SHA=r"^[0-9a-f]{64}$"
Capability=Literal["workspace_read","workspace_write","tests","git_commit","git_push"]
class StepPolicy(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
 step_id:str=Field(min_length=1,max_length=128,pattern=_ID); action:Literal["inspect","edit","test","git_commit","git_push"]; capabilities:list[Capability]=Field(default_factory=list,max_length=8); max_attempts:int=Field(default=1,ge=1,le=5); requires_gate:bool=False
 @field_validator("step_id")
 @classmethod
 def no_hidden(cls,value):
  if value.startswith("__"):raise ValueError("hidden step")
  return value
class HarnessTemplate(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
 template_id:str=Field(min_length=1,max_length=128,pattern=_ID); version:str=Field(min_length=1,max_length=32,pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$"); content_hash:str=Field(pattern=_SHA); signature:str=Field(min_length=1,max_length=256); capabilities:list[Capability]=Field(default_factory=list,max_length=8); steps:list[StepPolicy]=Field(min_length=1,max_length=16); description:str=Field(max_length=512)
class HarnessImport(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 template:HarnessTemplate; read_only:bool=True; enable_push:bool=False
class RunPlan(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 plan_id:str=Field(min_length=1,max_length=128,pattern=_ID); template_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); workspace_realpath:str=Field(min_length=1,max_length=4096); current_step:int=Field(ge=0,le=16); attempt:int=Field(ge=0,le=5); status:Literal["planned","running","awaiting_gate","succeeded","failed","cancelled"]; gate_status:Literal["not_required","required","approved"]="not_required"; diff:str=Field(default="",max_length=EXTENSION_POLICY.max_context_bytes); report:str=Field(default="",max_length=8192)
 @field_validator("diff","report")
 @classmethod
 def safe_text(cls,value):return redact(value)
class AdvanceRequest(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 plan_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); test_passed:bool=False; diff:str=Field(default="",max_length=EXTENSION_POLICY.max_context_bytes); tool_output:str=Field(default="",max_length=8192); gate:GateConsumeRequest|None=None
class ArtifactReport(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 plan_id:str=Field(min_length=1,max_length=128,pattern=_ID); status:Literal["succeeded","failed","running","awaiting_gate"]; diff:str=Field(default="",max_length=EXTENSION_POLICY.max_context_bytes); report:str=Field(default="",max_length=8192); published:bool=False
