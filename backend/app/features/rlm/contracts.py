"""Strict public RLM contracts; child agents never receive executable code."""
from __future__ import annotations
from enum import StrEnum
import json
from typing import Any, Literal
from pydantic import ConfigDict, Field, field_validator, model_validator
from app.core.extension_contracts import ContextEnvelope, ExtensionContract, EXTENSION_POLICY
from app.core.json_values import validate_json_value
from app.features.human_gates.contracts import GateConsumeRequest

class ChildAgentStatus(StrEnum):
    SUCCEEDED="succeeded"; FAILED="failed"; LIMITED="limited"; CANCELLED="cancelled"

class ChildAgentSpec(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    parent_run_id: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    provider: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    prompt: str=Field(min_length=1,max_length=16*1024)
    context: ContextEnvelope
    depth: int=Field(ge=1,le=EXTENSION_POLICY.max_rlm_depth)
    max_tokens: int=Field(default=1024,ge=1,le=8192)
    external_provider: bool=False
    external_dataflow_approved: bool=False
    external_approval_fingerprint: str|None=Field(default=None,pattern=r"^[0-9a-f]{64}$")
    requires_human_gate: bool=False
    human_gate: GateConsumeRequest|None=None

    @field_validator("prompt")
    @classmethod
    def bounded_prompt(cls,value: str)->str:
        if "\x00" in value or len(value.encode())>16*1024: raise ValueError("child prompt exceeds limit")
        return value

    @model_validator(mode="after")
    def external_approval(self)->"ChildAgentSpec":
        if self.external_provider and (not self.external_dataflow_approved or not self.external_approval_fingerprint): raise ValueError("external child provider requires approval fingerprint")
        if self.parent_run_id != self.run_id: raise ValueError("child run must remain bound to parent run")
        return self

class ChildAgentResult(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    child_run_id: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    parent_run_id: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    status: Literal["succeeded","failed","limited","cancelled"]
    source: Literal["untrusted"] = "untrusted"
    summary: str=Field(default="",max_length=16*1024)
    evidence: list[dict[str,Any]]=Field(default_factory=list,max_length=8)
    error_code: str|None=Field(default=None,max_length=64,pattern=r"^[a-z][a-z0-9_.-]{1,63}$")

    @field_validator("summary")
    @classmethod
    def bounded_summary(cls,value: str)->str:
        if "\x00" in value or len(value.encode())>16*1024: raise ValueError("child summary exceeds limit")
        return value

    @field_validator("evidence")
    @classmethod
    def bounded_evidence(cls,value: list[dict[str,Any]])->list[dict[str,Any]]:
        for item in value: validate_json_value(item)
        if len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode())>EXTENSION_POLICY.max_context_bytes: raise ValueError("child evidence exceeds limit")
        return value

class AggregateResult(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    status: Literal["succeeded","failed","limited","cancelled"]
    children: list[ChildAgentResult]=Field(default_factory=list,max_length=EXTENSION_POLICY.max_rlm_children)
    summary: str=Field(default="",max_length=16*1024)
    error_code: str|None=Field(default=None,max_length=64,pattern=r"^[a-z][a-z0-9_.-]{1,63}$")

    @field_validator("summary")
    @classmethod
    def bounded_summary(cls,value: str)->str:
        if len(value.encode())>16*1024: raise ValueError("aggregate summary exceeds limit")
        return value
