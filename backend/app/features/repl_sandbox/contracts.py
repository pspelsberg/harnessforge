"""Public contracts for the REPL sandbox slice."""
from __future__ import annotations
from enum import StrEnum
from typing import Any, Literal
import json
from pydantic import ConfigDict, Field, field_validator
from app.core.config import CAPS
from app.core.extension_contracts import ExtensionContract, EXTENSION_POLICY
from app.core.json_values import validate_json_value

class ReplMode(StrEnum):
    LOCAL_TRUST = "local_trust"

class ReplStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    LIMITED = "limited"
    CANCELLED = "cancelled"

class ReplExecuteRequest(ExtensionContract):
    model_config = ConfigDict(strict=True, extra="forbid")
    mode: Literal["local_trust"] = "local_trust"
    code: str = Field(min_length=1, max_length=EXTENSION_POLICY.max_repl_code_bytes)
    input_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def bounded_code(cls, value: str) -> str:
        if "\x00" in value or len(value.encode("utf-8")) > EXTENSION_POLICY.max_repl_code_bytes:
            raise ValueError("REPL code exceeds limit")
        return value

    @field_validator("input_data")
    @classmethod
    def bounded_input(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_json_value(value)
        if len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()) > EXTENSION_POLICY.max_context_bytes:
            raise ValueError("REPL input exceeds limit")
        return value

class ReplResult(ExtensionContract):
    model_config = ConfigDict(strict=True, extra="forbid")
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    status: Literal["succeeded", "failed", "limited", "cancelled"]
    trust_mode: Literal["local_trust"] = "local_trust"
    stdout: str = Field(default="", max_length=EXTENSION_POLICY.max_repl_output_bytes)
    result: Any = None
    error_code: str | None = Field(default=None, max_length=64, pattern=r"^[a-z][a-z0-9_.-]{1,63}$")

    @field_validator("result")
    @classmethod
    def bounded_result(cls, value: Any) -> Any:
        validate_json_value(value)
        return value

class ReplSessionInfo(ExtensionContract):
    model_config = ConfigDict(strict=True, extra="forbid")
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    status: Literal["active", "closed"]
    cells: int = Field(ge=0, le=1024)
