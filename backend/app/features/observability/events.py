"""Validated, redacted run event contract."""
from __future__ import annotations
from typing import Any
import json
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.core.config import CAPS
from app.core.security.redaction import redact_payload
from app.core.json_values import validate_json_value
EVENT_TYPES={"run.created","run.started","run.validating","run.paused","run.resumed","run.running","run.succeeded","run.failed","run.cancelled","run.limit_exceeded","run.completed","node.queued","node.running","node.succeeded","node.failed","state.diff","llm.token_stream","rag.results","tool.output","iteration.update","state.diff"}
class Event(BaseModel):
    model_config=ConfigDict(extra="forbid")
    type:str=Field(min_length=1,max_length=64,pattern=r"^[a-z][a-z0-9_.-]*$")
    run_id:str=Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9._-]+$")
    payload:dict[str,Any]
    @field_validator("type")
    @classmethod
    def known_type(cls,value):
        if value not in EVENT_TYPES: raise ValueError("unknown event type")
        return value
    @field_validator("payload")
    @classmethod
    def bounded(cls,value):
        validate_json_value(value)
        if len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode())>CAPS.max_event_bytes: raise ValueError("event payload too large")
        return value
def redact_event(event:Event)->Event:
    data=event.model_dump(mode="json");data["payload"]=redact_payload(data["payload"]);return Event.model_validate(data)
