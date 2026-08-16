"""Strict index job, file record and query projection contracts."""
from __future__ import annotations
from typing import Any,Literal
from pydantic import ConfigDict,Field,field_validator
from app.core.extension_contracts import ExtensionContract,EXTENSION_POLICY
_SHA=r"^[0-9a-f]{64}$"; _ID=r"^[A-Za-z0-9._-]{1,128}$"
class FileRecord(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid",frozen=True)
 relative_path:str=Field(min_length=1,max_length=4096); size:int=Field(ge=0,le=EXTENSION_POLICY.max_index_file_bytes); mime:str=Field(min_length=1,max_length=128); sha256:str=Field(pattern=_SHA); mtime_ns:int=Field(ge=0); symbols:list[str]=Field(default_factory=list,max_length=512); snippet:str=Field(default="",max_length=8192); parser_error:str|None=Field(default=None,max_length=512)
 @field_validator("snippet","parser_error")
 @classmethod
 def no_secrets(cls,value):
  if value and "\x00" in value:raise ValueError("binary content")
  return value
class IndexJob(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 job_id:str=Field(min_length=1,max_length=128,pattern=_ID); session_id:str=Field(min_length=1,max_length=128,pattern=_ID); workspace_realpath:str=Field(min_length=1,max_length=4096); status:Literal["queued","running","succeeded","failed","paused"]="queued"; queue_depth:int=Field(ge=0,le=256); indexed_files:int=Field(ge=0,le=10000); version:int=Field(ge=0); error:str|None=Field(default=None,max_length=512)
class IndexStatus(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 status:Literal["idle","queued","running","succeeded","failed","paused"]; version:int=Field(ge=0); indexed_files:int=Field(ge=0); queue_depth:int=Field(ge=0,le=256); last_sync:str|None=None; error:str|None=Field(default=None,max_length=512)
class IndexQuery(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 session_id:str=Field(min_length=1,max_length=128,pattern=_ID); query:str=Field(min_length=1,max_length=256); limit:int=Field(default=10,ge=1,le=50)
class IndexResult(ExtensionContract):
 model_config=ConfigDict(strict=True,extra="forbid")
 query:str; results:list[FileRecord]=Field(max_length=50); context_label:Literal["untrusted_workspace_context"]="untrusted_workspace_context"
