"""Strict contracts for immutable checkpoints and controlled forks."""
from __future__ import annotations
from typing import Any, Literal
from pathlib import Path
import json
from pydantic import ConfigDict, Field, field_validator
from app.core.extension_contracts import ExtensionContract, EXTENSION_POLICY
from app.core.json_values import validate_json_value
from app.features.execution.public import AgentState, Reducer

_SHA=r"^[0-9a-f]{64}$"; _ID=r"^[A-Za-z0-9._-]{1,128}$"

def _workspace_value(value: str)->str:
    if "\x00" in value or any(ord(char)<32 for char in value) or "\\" in value or not value.startswith("/") or value.startswith("//") or any(part in {".",".."} for part in value.split("/")) or str(Path(value)) != value:
        raise ValueError("workspace path must be absolute, canonical and control-free")
    return value

class CheckpointView(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
    checkpoint_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    graph_version: str=Field(pattern=_SHA)
    workspace_realpath: str=Field(min_length=1,max_length=4096)

    @field_validator("workspace_realpath")
    @classmethod
    def safe_workspace(cls,value: str)->str: return _workspace_value(value)
    schema_version: Literal["1"]="1"
    step: int=Field(ge=0,le=10_000_000)
    state_hash: str=Field(pattern=_SHA)
    state: dict[str,Any]

    @field_validator("state")
    @classmethod
    def bounded_state(cls,value: dict[str,Any])->dict[str,Any]:
        validate_json_value(value)
        if len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode())>5*1024*1024: raise ValueError("checkpoint state exceeds limit")
        return value

class CreateCheckpointRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    graph_version: str=Field(pattern=_SHA)
    workspace_realpath: str=Field(min_length=1,max_length=4096)

    @field_validator("workspace_realpath")
    @classmethod
    def safe_workspace(cls,value: str)->str: return _workspace_value(value)
    step: int=Field(ge=0,le=10_000_000)
    state: dict[str,Any]

    @field_validator("state")
    @classmethod
    def bounded_state(cls,value: dict[str,Any])->dict[str,Any]:
        validate_json_value(value)
        if len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode())>5*1024*1024: raise ValueError("checkpoint state exceeds limit")
        return value

class ForkRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    checkpoint_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    session_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    graph_version: str=Field(pattern=_SHA)
    workspace_realpath: str=Field(min_length=1,max_length=4096)

    @field_validator("workspace_realpath")
    @classmethod
    def safe_workspace(cls,value: str)->str: return _workspace_value(value)
    reducers: list[Reducer]=Field(default_factory=list,max_length=32)
    simulate_external: bool=True

class ForkLineage(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
    fork_run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    parent_run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    checkpoint_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    graph_version: str=Field(pattern=_SHA)
    workspace_realpath: str=Field(min_length=1,max_length=4096)

    @field_validator("workspace_realpath")
    @classmethod
    def safe_workspace(cls,value: str)->str: return _workspace_value(value)
    depth: int=Field(ge=1,le=EXTENSION_POLICY.max_fork_depth)
    approvals_reissued: bool=True
    external_actions: Literal["simulated","approval_required"]="simulated"

class ForkResult(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    lineage: ForkLineage
    state: dict[str,Any]
    required_new_approvals: list[str]=Field(default_factory=list,max_length=32)
