"""Versioned public contracts shared by Phase-2 extension slices.

This module intentionally contains data contracts and policy bounds only. It must
not import any feature implementation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import json
import re
from typing import Any, Literal
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import CAPS
from app.core.json_values import validate_json_value
from app.core.security.redaction import redact_payload


_ID = r"^[A-Za-z0-9._-]{1,128}$"
_NAME = r"^[a-z][a-z0-9_.-]{1,63}$"
_SHA256 = r"^[0-9a-f]{64}$"
_BINDING = r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$"


class ExtensionContract(BaseModel):
    """Common version marker for wire-visible extension DTOs."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    contract_version: Literal["1"] = "1"


class ExtensionErrorCode(StrEnum):
    """Stable error-code namespace without coupling contracts to feature code."""

    INVALID_INPUT = "extension.invalid_input"
    POLICY_DENIED = "extension.policy_denied"
    LIMIT_EXCEEDED = "extension.limit_exceeded"
    CANCELLED = "extension.cancelled"
    EXPIRED = "extension.expired"
    UPSTREAM_FAILED = "extension.upstream_failed"


EXTENSION_EVENT_PHASES = frozenset({"started", "progress", "succeeded", "failed", "cancelled", "limit_exceeded"})


class ExtensionRetentionPolicy(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    events_days: int = Field(default=30, ge=1, le=365)
    checkpoints_days: int = Field(default=30, ge=1, le=365)
    suggestions_days: int = Field(default=30, ge=1, le=365)


EXTENSION_RETENTION = ExtensionRetentionPolicy()


class ExtensionControl(ExtensionContract):
    command: Literal["cancel", "interrupt"]
    request_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    reason: str = Field(default="", max_length=512)


class ExtensionPolicy(BaseModel):
    """Hard, centrally defined budgets for every Phase-2 extension."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    max_rlm_depth: int = Field(default=3, ge=1, le=3)
    max_rlm_children: int = Field(default=8, ge=1, le=32)
    max_context_bytes: int = Field(default=128 * 1024, ge=1024, le=CAPS.max_state_bytes)
    max_event_bytes: int = Field(default=CAPS.max_event_bytes, ge=1024, le=CAPS.max_state_bytes)
    max_repl_code_bytes: int = Field(default=64 * 1024, ge=1024, le=CAPS.max_state_bytes)
    max_repl_output_bytes: int = Field(default=64 * 1024, ge=1024, le=CAPS.max_event_bytes)
    max_repl_seconds: float = Field(default=30.0, gt=0, le=CAPS.max_run_seconds)
    max_repl_memory_bytes: int = Field(default=256 * 1024 * 1024, ge=1024 * 1024, le=1024 * 1024 * 1024)
    max_mcp_servers: int = Field(default=16, ge=1, le=64)
    max_mcp_schema_bytes: int = Field(default=128 * 1024, ge=1024, le=CAPS.max_event_bytes)
    max_mcp_response_bytes: int = Field(default=CAPS.max_event_bytes, ge=1024, le=CAPS.max_state_bytes)
    max_mcp_calls_per_run: int = Field(default=32, ge=1, le=256)
    max_fork_depth: int = Field(default=8, ge=1, le=32)
    max_forks_per_run: int = Field(default=16, ge=1, le=128)
    max_approval_ttl_seconds: int = Field(default=15 * 60, ge=1, le=24 * 60 * 60)
    max_refiner_patch_bytes: int = Field(default=128 * 1024, ge=1024, le=CAPS.max_state_bytes)
    max_index_file_bytes: int = Field(default=2 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)


EXTENSION_POLICY = ExtensionPolicy()


def _bounded_json(value: Any, *, maximum: int, label: str) -> Any:
    try:
        validate_json_value(value)
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be bounded JSON") from exc
    if len(encoded) > maximum:
        raise ValueError(f"{label} exceeds size limit")
    return value


def _aware(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(timezone.utc)


class CapabilityDescriptor(ExtensionContract):
    """Capability-based provider/tool description; never a secret-bearing config."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=128, pattern=_ID)
    kind: str = Field(min_length=1, max_length=64, pattern=_NAME)
    version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._+-]+$")
    capabilities: list[str] = Field(default_factory=list, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capabilities")
    @classmethod
    def valid_capabilities(cls, values: list[str]) -> list[str]:
        if any(not isinstance(value, str) or not re.fullmatch(_NAME, value) for value in values):
            raise ValueError("capabilities must be names")
        if len(set(values)) != len(values):
            raise ValueError("capabilities must be unique")
        return values

    @field_validator("metadata")
    @classmethod
    def bounded_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        clean = redact_payload(value)
        return _bounded_json(clean, maximum=EXTENSION_POLICY.max_context_bytes, label="capability metadata")


class ContextEnvelope(ExtensionContract):
    """A context value with explicit trust and binding provenance."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    source: Literal["trusted", "untrusted"]
    origin: str = Field(min_length=1, max_length=128, pattern=_ID)
    bindings: list[str] = Field(default_factory=list, max_length=32)
    content: Any

    @field_validator("bindings")
    @classmethod
    def valid_bindings(cls, values: list[str]) -> list[str]:
        if any(not isinstance(value, str) or not re.fullmatch(_BINDING, value) for value in values):
            raise ValueError("invalid context binding")
        if len(set(values)) != len(values):
            raise ValueError("context bindings must be unique")
        return values

    @field_validator("content")
    @classmethod
    def bounded_content(cls, value: Any) -> Any:
        return _bounded_json(value, maximum=EXTENSION_POLICY.max_context_bytes, label="context")


class ApprovalRequest(ExtensionContract):
    """Replay-resistant, expiring request for a human decision."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    request_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    nonce: str = Field(min_length=32, max_length=64, pattern=r"^[A-Za-z0-9_-]{32,64}$")
    run_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    node_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    action: str = Field(min_length=1, max_length=128, pattern=_NAME)
    action_fingerprint: str = Field(pattern=_SHA256)
    workspace_realpath: str = Field(min_length=1, max_length=4096)
    issued_at: datetime
    expires_at: datetime
    preview: dict[str, Any] = Field(default_factory=dict)

    @field_validator("workspace_realpath")
    @classmethod
    def valid_workspace_realpath(cls, value: str) -> str:
        if "\x00" in value or any(ord(char) < 32 for char in value) or "\\" in value or not value.startswith("/") or value.startswith("//"):
            raise ValueError("workspace_realpath must be a canonical absolute path")
        if any(part in {".", ".."} for part in PurePosixPath(value).parts):
            raise ValueError("workspace_realpath must not contain traversal segments")
        return value

    @field_validator("issued_at", "expires_at")
    @classmethod
    def timezone_required(cls, value: datetime, info) -> datetime:
        return _aware(value, info.field_name)

    @field_validator("preview")
    @classmethod
    def bounded_preview(cls, value: dict[str, Any]) -> dict[str, Any]:
        # Preview is displayed to a human and therefore is redacted at the
        # contract boundary, not only when it is persisted.
        clean = redact_payload(value)
        return _bounded_json(clean, maximum=EXTENSION_POLICY.max_context_bytes, label="approval preview")

    @model_validator(mode="after")
    def valid_expiry(self) -> "ApprovalRequest":
        if self.expires_at <= self.issued_at:
            raise ValueError("approval expiry must be after issue time")
        if (self.expires_at - self.issued_at).total_seconds() > EXTENSION_POLICY.max_approval_ttl_seconds:
            raise ValueError("approval TTL exceeds policy")
        return self


class ApprovalDecision(ExtensionContract):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    request_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    nonce: str = Field(min_length=32, max_length=64, pattern=r"^[A-Za-z0-9_-]{32,64}$")
    decision: Literal["approved", "denied"]
    decided_at: datetime
    reason: str = Field(default="", max_length=512)

    @field_validator("decided_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return _aware(value, "decided_at")


class CheckpointRef(ExtensionContract):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    checkpoint_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    run_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    schema_version: Literal["1"]
    step: int = Field(ge=0, le=10_000_000)
    state_hash: str = Field(pattern=_SHA256)
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return _aware(value, "created_at")


class ForkRef(ExtensionContract):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    fork_run_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    parent_run_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    checkpoint_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    lineage_depth: int = Field(ge=1, le=EXTENSION_POLICY.max_fork_depth)


class ExtensionEvent(ExtensionContract):
    """Redacted, bounded event envelope for future extension namespaces."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    namespace: str = Field(min_length=1, max_length=64, pattern=_NAME)
    name: str = Field(min_length=1, max_length=64, pattern=_NAME)
    run_id: str = Field(min_length=1, max_length=128, pattern=_ID)
    phase: str = Field(default="progress", min_length=1, max_length=32, pattern=_NAME)
    error_code: str | None = Field(default=None, max_length=64, pattern=_NAME)
    payload: dict[str, Any]

    @field_validator("phase")
    @classmethod
    def valid_phase(cls, value: str) -> str:
        if value not in EXTENSION_EVENT_PHASES:
            raise ValueError("invalid extension event phase")
        return value

    @model_validator(mode="after")
    def valid_error_semantics(self) -> "ExtensionEvent":
        terminal = self.phase in {"failed", "cancelled", "limit_exceeded"}
        if terminal and not self.error_code:
            raise ValueError("terminal extension events require an error code")
        if not terminal and self.error_code is not None:
            raise ValueError("non-terminal extension events cannot carry an error code")
        return self

    @field_validator("payload")
    @classmethod
    def redact_and_bound(cls, value: dict[str, Any]) -> dict[str, Any]:
        clean = redact_payload(value)
        return _bounded_json(clean, maximum=EXTENSION_POLICY.max_event_bytes, label="extension event")
