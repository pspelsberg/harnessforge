"""Strict human-gate contracts and redacted action previews."""
from __future__ import annotations
from typing import Any, Literal
import json
from pydantic import ConfigDict, Field, field_validator, model_validator
from app.core.extension_contracts import ExtensionContract, EXTENSION_POLICY
from app.core.json_values import validate_json_value
from app.core.security.redaction import redact_payload

GateClass=Literal["tool_write","git_commit","git_push","external_dataflow","mcp_call","rlm_spawn"]
GateStatus=Literal["pending","approved","denied","expired","cancelled","consumed"]
_ID=r"^[A-Za-z0-9._-]{1,128}$"
_SHA=r"^[0-9a-f]{64}$"

def _workspace_value(value: str)->str:
    if "\x00" in value or any(ord(char)<32 for char in value) or "\\" in value or not value.startswith("/") or value.startswith("//"):
        raise ValueError("workspace path must be absolute and control-free")
    if any(part in {".",".."} for part in value.split("/")): raise ValueError("workspace path contains traversal")
    return value

class ActionPreview(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    action: str=Field(min_length=1,max_length=128,pattern=r"^[a-z][a-z0-9_.-]{1,63}$")
    command: str=Field(default="",max_length=4096)
    diff: str=Field(default="",max_length=EXTENSION_POLICY.max_context_bytes)
    dataflow: str=Field(default="local",max_length=128)
    risk: Literal["low","medium","high","critical"]="high"
    write_targets: list[str]=Field(default_factory=list,max_length=64)

    @field_validator("command","diff","dataflow")
    @classmethod
    def redact_text(cls,value: str)->str:
        if "\x00" in value: raise ValueError("preview contains forbidden character")
        return str(redact_payload(value))

    @field_validator("write_targets")
    @classmethod
    def bounded_targets(cls,value: list[str])->list[str]:
        if any("\x00" in target or len(target)>4096 for target in value): raise ValueError("invalid write target")
        return [str(redact_payload(target)) for target in value]

class GateRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    request_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    nonce: str=Field(min_length=32,max_length=64,pattern=r"^[A-Za-z0-9_-]{32,64}$")
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    node_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    graph_version: str=Field(pattern=_SHA)
    workspace_realpath: str=Field(min_length=1,max_length=4096)
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    gate_class: GateClass
    action_fingerprint: str=Field(pattern=_SHA)
    preview: ActionPreview
    issued_at: str=Field(min_length=1,max_length=64)
    expires_at: str=Field(min_length=1,max_length=64)
    status: GateStatus="pending"

    @field_validator("workspace_realpath")
    @classmethod
    def safe_workspace(cls,value: str)->str: return _workspace_value(value)

    @field_validator("issued_at", "expires_at")
    @classmethod
    def valid_timestamp(cls,value: str)->str:
        from datetime import datetime
        try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        except ValueError as exc: raise ValueError("invalid gate timestamp") from exc
        if parsed.tzinfo is None: raise ValueError("gate timestamp must be timezone-aware")
        return value

class GateCreateRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    node_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    graph_version: str=Field(pattern=_SHA)
    workspace_realpath: str=Field(min_length=1,max_length=4096)
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    gate_class: GateClass
    preview: ActionPreview
    ttl_seconds: int=Field(default=300,ge=1,le=EXTENSION_POLICY.max_approval_ttl_seconds)

    @field_validator("workspace_realpath")
    @classmethod
    def safe_workspace(cls,value: str)->str: return _workspace_value(value)

class GateRecord(GateRequest):
    """Persisted projection; status transitions are controlled by the store."""
    pass

class GateDecision(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    request_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    nonce: str=Field(min_length=32,max_length=64,pattern=r"^[A-Za-z0-9_-]{32,64}$")
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    decision: Literal["approved","denied"]
    reason: str=Field(default="",max_length=512)

    @field_validator("reason")
    @classmethod
    def redact_reason(cls,value: str)->str: return str(redact_payload(value))

class GateConsumeRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    request_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    nonce: str=Field(min_length=32,max_length=64,pattern=r"^[A-Za-z0-9_-]{32,64}$")
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    action_fingerprint: str=Field(pattern=_SHA)

class GateOutcome(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    request_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    status: GateStatus
    reason: str=Field(default="",max_length=512)
