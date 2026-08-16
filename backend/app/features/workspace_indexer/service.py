"""Workspace index lifecycle with bounded scan and read-only query."""
from __future__ import annotations
import asyncio,uuid
from datetime import datetime,timezone
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.workspace_indexer.contracts import IndexJob,IndexQuery,IndexResult,IndexStatus
from app.features.workspace_indexer.scanner import WorkspaceScanner,ScanError
from app.features.workspace_indexer.writer import IndexWriter,IndexWriterError
class IndexerError(RuntimeError):pass
class WorkspaceIndexService:
 def __init__(self,workspace:str|Path):
  try:self.boundary=WorkspaceBoundary(workspace)
  except UnsafePathError as exc:raise IndexerError("invalid index workspace") from exc
  self.writer=IndexWriter(self.boundary);self.scanner=WorkspaceScanner(self.boundary);self._lock=asyncio.Lock();self._status="idle";self._queue=0;self._error=None
 def _workspace(self,value:str):
  try:resolved=Path(value).resolve(strict=True)
  except (OSError,RuntimeError) as exc:raise IndexerError("invalid workspace") from exc
  if resolved!=self.boundary.workspace:raise IndexerError("workspace mismatch")
 async def status(self)->IndexStatus:
  version,last,count=await self.writer.status();return IndexStatus(status=self._status,version=version,indexed_files=count,queue_depth=self._queue,last_sync=last,error=self._error)
 async def rebuild(self,session_id:str,workspace_realpath:str)->IndexJob:
  self._workspace(workspace_realpath)
  async with self._lock:
   if self._status=="paused": raise IndexerError("index is paused")
   self._status="running";self._error=None
   try:records=self.scanner.scan();version=await self.writer.rebuild(records,datetime.now(timezone.utc).isoformat());self._status="succeeded";return IndexJob(job_id="index-"+uuid.uuid4().hex,session_id=session_id,workspace_realpath=str(self.boundary.workspace),status="succeeded",queue_depth=0,indexed_files=len(records),version=version)
   except (ScanError,IndexWriterError,OSError) as exc:self._status="failed";self._error="index rebuild failed";raise IndexerError("index rebuild failed") from exc
 async def pause(self):self._status="paused"
 async def resume(self):
  if self._status=="paused":self._status="idle"
 async def query(self,request:IndexQuery)->IndexResult:
  results=await self.writer.query(request.query,request.limit);return IndexResult(query=request.query,results=results)
