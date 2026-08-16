"""Persistent suggestion inbox with compare-and-set status transitions."""
from __future__ import annotations
from contextlib import asynccontextmanager
import asyncio
import json
from pathlib import Path
import aiosqlite
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.continual_refiner.contracts import Suggestion
class ReviewStoreError(RuntimeError): pass
class ReviewStore:
 def __init__(self,workspace: str|Path):
  try: self.boundary=WorkspaceBoundary(workspace); self.path=self.boundary.resolve(".harnessforge/refiner-reviews.db")
  except UnsafePathError as exc: raise ReviewStoreError("invalid refiner workspace") from exc
  self._ready=False; self._init_lock=asyncio.Lock()
 @asynccontextmanager
 async def _connect(self):
  async with aiosqlite.connect(self.path) as db: yield db
 async def _ensure(self):
  if self._ready:return
  async with self._init_lock:
   if self._ready:return
   await self._initialize()
 async def _initialize(self):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  async with self._connect() as db:
   await db.execute("CREATE TABLE IF NOT EXISTS suggestions (suggestion_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,session_id TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL,backup_path TEXT)"); await db.commit()
  self._ready=True
 async def save(self,suggestion:Suggestion):
  await self._ensure()
  try:
   async with self._connect() as db: await db.execute("INSERT INTO suggestions VALUES (?,?,?,?,?,NULL)",(suggestion.suggestion_id,suggestion.run_id,suggestion.session_id,suggestion.status,suggestion.model_dump_json())); await db.commit()
  except aiosqlite.IntegrityError as exc: raise ReviewStoreError("suggestion already exists") from exc
  return suggestion
 async def get(self,suggestion_id:str)->Suggestion:
  await self._ensure()
  async with self._connect() as db:
   cur=await db.execute("SELECT status,payload FROM suggestions WHERE suggestion_id=?",(suggestion_id,)); row=await cur.fetchone()
  if not row: raise ReviewStoreError("suggestion unavailable")
  data=json.loads(row[1]); data["status"]=row[0]; return Suggestion.model_validate(data)
 async def list(self,session_id:str,run_id:str|None=None)->list[Suggestion]:
  await self._ensure(); query="SELECT status,payload FROM suggestions WHERE session_id=?"; args=[session_id]
  if run_id is not None: query+=" AND run_id=?"; args.append(run_id)
  async with self._connect() as db:
   cur=await db.execute(query,tuple(args)); rows=await cur.fetchall()
  result=[]
  for status,payload in rows:
   data=json.loads(payload); data["status"]=status; result.append(Suggestion.model_validate(data))
  return result
 async def backup_path(self,suggestion_id:str,session_id:str)->str|None:
  await self._ensure()
  async with self._connect() as db:
   cur=await db.execute("SELECT backup_path FROM suggestions WHERE suggestion_id=? AND session_id=?",(suggestion_id,session_id)); row=await cur.fetchone()
  if not row: raise ReviewStoreError("suggestion unavailable")
  return row[0]
 async def transition(self,suggestion_id:str,session_id:str,old:str,new:str,backup_path:str|None=None)->Suggestion:
  await self._ensure()
  async with self._connect() as db:
   await db.execute("BEGIN IMMEDIATE"); cur=await db.execute("SELECT status,payload FROM suggestions WHERE suggestion_id=? AND session_id=?",(suggestion_id,session_id)); row=await cur.fetchone()
   if not row or row[0]!=old: await db.rollback(); raise ReviewStoreError("suggestion state conflict")
   await db.execute("UPDATE suggestions SET status=?,backup_path=? WHERE suggestion_id=? AND status=?",(new,backup_path,suggestion_id,old)); await db.commit()
  data=json.loads(row[1]); data["status"]=new; return Suggestion.model_validate(data)
