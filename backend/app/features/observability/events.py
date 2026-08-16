"""Validated, redacted run event contract."""
from __future__ import annotations
from typing import Any
import json
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.core.config import CAPS
from app.core.security.redaction import redact
from app.core.json_values import validate_json_value
EVENT_TYPES={"run.created","run.started","run.validating","run.paused","run.resumed","run.running","run.succeeded","run.failed","run.cancelled","run.limit_exceeded","node.queued","node.running","node.succeeded","node.failed","state.diff","llm.token_stream","rag.results","tool.output","iteration.update","state.diff"}
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
_SECRET_KEYS={"authorization","cookie","set-cookie","api_key","apikey","access_token","refresh_token","token","secret","password"}
def _redact_value(value,*,key=None):
    if key and key.casefold().replace("-","_") in _SECRET_KEYS:return "[REDACTED]"
    if isinstance(value,str):return redact(value)
    if isinstance(value,list):return [_redact_value(item) for item in value[:128]]
    if isinstance(value,dict):return {str(k):_redact_value(v,key=str(k)) for k,v in list(value.items())[:64]}
    return value
def redact_event(event:Event)->Event:
    data=event.model_dump(mode="json");data["payload"]=_redact_value(data["payload"]);return Event.model_validate(data)
