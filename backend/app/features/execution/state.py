"""Bounded AgentState and declarative reducer operations."""
from __future__ import annotations

from enum import StrEnum
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.core.config import CAPS
from app.core.json_values import validate_json_value


class StateLimitError(ValueError):
    """Raised when a state mutation would exceed a hard runtime limit."""


class ReducerOp(StrEnum):
    SET = "SET"
    APPEND_LIST = "APPEND_LIST"
    MERGE_DICT = "MERGE_DICT"
    INCREMENT = "INCREMENT"


_STATE_FIELDS = {"messages", "query", "retrieved_context", "tool_results", "last_output", "iteration", "metadata", "custom_state"}
_PATH_PART = r"[A-Za-z_][A-Za-z0-9_]*"


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    query: str = ""
    retrieved_context: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    last_output: Any = None
    iteration: int = Field(default=0, ge=0, le=CAPS.max_loop_iterations)
    metadata: dict[str, Any] = Field(default_factory=dict)
    custom_state: dict[str, Any] = Field(default_factory=dict)

    @field_validator("messages", "retrieved_context", "tool_results", "metadata", "custom_state", "last_output", mode="before")
    @classmethod
    def validate_json_fields(cls, value: Any, info: ValidationInfo) -> Any:
        # ``last_output`` is allowed to approach the aggregate state cap; the
        # model-level size check then rejects values that leave no room for the
        # remaining state. Other fields retain the smaller JSON value cap.
        if info.field_name == "last_output" and isinstance(value, str) and len(value.encode("utf-8")) <= CAPS.max_state_bytes:
            return value
        try:
            validate_json_value(value)
        except ValueError as exc:
            raise ValueError("state fields must contain bounded JSON values") from exc
        return value

    @model_validator(mode="after")
    def enforce_size(self) -> "AgentState":
        if _size(self) > CAPS.max_state_bytes:
            raise StateLimitError("state size limit exceeded")
        return self


class Reducer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: ReducerOp
    # Dotted paths are deliberately limited to custom_state and existing top-level
    # dict fields; arbitrary object traversal is never permitted.
    target: str = Field(min_length=1, max_length=128, pattern=rf"^{_PATH_PART}(\.{_PATH_PART}){{0,3}}$")
    value: Any = None

    @field_validator("value")
    @classmethod
    def safe_value(cls, value: Any) -> Any:
        try:
            validate_json_value(value)
        except ValueError as exc:
            if isinstance(value, str) and len(value.encode("utf-8")) <= CAPS.max_state_bytes:
                return value
            if isinstance(value, str):
                raise StateLimitError("state value exceeds limit") from exc
            raise
        return value

    @field_validator("target")
    @classmethod
    def safe_target(cls, value: str) -> str:
        parts = value.split(".")
        if any(part.startswith("__") or part in {"model_config", "__dict__", "__class__"} for part in parts):
            raise ValueError("target is reserved")
        if len(parts) > 1 and parts[0] not in {"custom_state", "metadata"}:
            raise ValueError("nested targets are limited to state dictionaries")
        if value in {"custom_state", "metadata"}:
            # Whole-dictionary replacement/merge would bypass key/path governance.
            raise ValueError("dictionary targets require a dotted path")
        return value


def _size(state: AgentState) -> int:
    return len(json.dumps(state.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")).encode())


def _get_target(state: AgentState, target: str) -> tuple[Any, str]:
    parts = target.split(".")
    if not hasattr(state, parts[0]):
        raise ValueError("target does not exist")
    parent: Any = state
    for part in parts[:-1]:
        if isinstance(parent, BaseModel):
            parent = getattr(parent, part, None)
        elif isinstance(parent, dict):
            parent = parent.get(part)
        else:
            parent = None
        if not isinstance(parent, dict):
            raise ValueError("target path does not exist")
    if isinstance(parent, BaseModel):
        if parts[-1] not in _STATE_FIELDS:
            raise ValueError("target does not exist")
        return parent, parts[-1]
    if isinstance(parent, dict):
        # SET may create a new custom/metadata key; the parent path is still
        # validated and dictionary keys remain bounded JSON values.
        return parent, parts[-1]
    raise ValueError("target path does not exist")


def _read(parent: Any, key: str) -> Any:
    return getattr(parent, key) if isinstance(parent, BaseModel) else parent[key]


def _write(parent: Any, key: str, value: Any) -> None:
    if isinstance(parent, BaseModel):
        # Assignment validation runs before the aggregate cap can be checked
        # and turns an oversized reducer into an opaque field error. The value
        # is validated atomically below via ``model_validate`` after the cap.
        object.__setattr__(parent, key, value)
    else:
        parent[key] = value


def apply_reducer(state: AgentState, reducer: Reducer) -> AgentState:
    candidate = state.model_copy(deep=True)
    parent, key = _get_target(candidate, reducer.target)
    current = _read(parent, key)
    if reducer.op == ReducerOp.SET:
        _write(parent, key, reducer.value)
    elif reducer.op == ReducerOp.APPEND_LIST:
        if not isinstance(current, list):
            raise TypeError("target is not a list")
        current.append(reducer.value)
    elif reducer.op == ReducerOp.MERGE_DICT:
        if not isinstance(current, dict) or not isinstance(reducer.value, dict):
            raise TypeError("merge requires dictionaries")
        current.update(reducer.value)
    elif reducer.op == ReducerOp.INCREMENT:
        if not isinstance(current, int) or isinstance(current, bool) or isinstance(reducer.value, bool) or not isinstance(reducer.value, int):
            raise TypeError("increment requires integers")
        _write(parent, key, current + reducer.value)
    if _size(candidate) > CAPS.max_state_bytes:
        raise StateLimitError("state size limit exceeded")
    validated = AgentState.model_validate(candidate.model_dump(mode="python"))
    state.__dict__.clear()
    state.__dict__.update(validated.__dict__)
    return state
