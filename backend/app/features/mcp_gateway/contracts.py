"""Strict, secret-free MCP manifest and call contracts."""
from __future__ import annotations
from typing import Any, Literal
import json
import re
from pydantic import ConfigDict, Field, field_validator, model_validator
from app.core.extension_contracts import ExtensionContract, EXTENSION_POLICY
from app.core.json_values import validate_json_value

_TRANSPORT=Literal["stdio","http","sse"]
_ID=r"^[A-Za-z0-9._-]{1,128}$"
_SHA=r"^[0-9a-f]{64}$"

def _bounded(value: Any, cap: int, label: str)->Any:
    validate_json_value(value)
    if len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode())>cap: raise ValueError(f"{label} exceeds limit")
    return value

class ServerManifest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    server_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    name: str=Field(min_length=1,max_length=128)
    transport: _TRANSPORT
    command: str|None=Field(default=None,min_length=1,max_length=4096)
    args: list[str]=Field(default_factory=list,max_length=32)
    endpoint: str|None=Field(default=None,max_length=2048)
    workspace_path: str|None=Field(default=None,max_length=4096)
    command_sha256: str|None=Field(default=None,pattern=_SHA)
    capabilities: list[str]=Field(default_factory=list,max_length=64)
    approved: bool=False
    approval_fingerprint: str|None=Field(default=None,pattern=_SHA)

    @field_validator("args")
    @classmethod
    def bounded_args(cls,value: list[str])->list[str]:
        if any("\x00" in arg or len(arg)>1024 for arg in value): raise ValueError("invalid MCP arguments")
        return value

    @field_validator("capabilities")
    @classmethod
    def bounded_capabilities(cls,value: list[str])->list[str]:
        if any(not re.fullmatch(r"^[a-z][a-z0-9_.-]{0,63}$",item) for item in value) or len(set(value))!=len(value): raise ValueError("invalid MCP capability")
        return value

    @model_validator(mode="after")
    def transport_requirements(self)->"ServerManifest":
        if self.transport=="stdio":
            if not self.command or not self.workspace_path or not self.command_sha256 or self.endpoint is not None: raise ValueError("stdio manifest requires bounded command/workspace/hash")
        elif not self.endpoint or self.command is not None or self.args or self.workspace_path is not None or self.command_sha256 is not None:
            raise ValueError("network manifest requires endpoint only")
        if self.approved and not self.approval_fingerprint: raise ValueError("approved MCP server requires fingerprint")
        return self

class ToolDescriptor(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    server_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    name: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9_.-]+$")
    description: str=Field(default="",max_length=4096)
    input_schema: dict[str,Any]=Field(default_factory=dict)

    @field_validator("input_schema")
    @classmethod
    def bounded_schema(cls,value: dict[str,Any])->dict[str,Any]:
        return _bounded(value,EXTENSION_POLICY.max_mcp_schema_bytes,"MCP schema")

class ResourceDescriptor(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    server_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    uri: str=Field(min_length=1,max_length=2048)
    name: str=Field(min_length=1,max_length=128)
    description: str=Field(default="",max_length=4096)

class McpCallRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    server_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    tool_name: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9_.-]+$")
    arguments: dict[str,Any]=Field(default_factory=dict)
    approval_fingerprint: str|None=Field(default=None,pattern=_SHA)

    @field_validator("arguments")
    @classmethod
    def bounded_arguments(cls,value: dict[str,Any])->dict[str,Any]:
        return _bounded(value,EXTENSION_POLICY.max_context_bytes,"MCP arguments")

class McpCallResult(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    run_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    server_id: str=Field(min_length=1,max_length=128,pattern=_ID)
    tool_name: str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9_.-]+$")
    status: Literal["succeeded","failed","limited","cancelled"]
    source: Literal["untrusted"]="untrusted"
    content: Any=None
    error_code: str|None=Field(default=None,max_length=64,pattern=r"^[a-z][a-z0-9_.-]{1,63}$")

    @field_validator("content")
    @classmethod
    def bounded_content(cls,value: Any)->Any:
        return _bounded(value,EXTENSION_POLICY.max_mcp_response_bytes,"MCP response")
