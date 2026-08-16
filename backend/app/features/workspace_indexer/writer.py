"""Atomic versioned SQLite index writer and read-only retrieval."""
from __future__ import annotations
from contextlib import asynccontextmanager
import asyncio
import json,uuid
from pathlib import Path
import aiosqlite
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.workspace_indexer.contracts import FileRecord,IndexResult
class IndexWriterError(RuntimeError):pass
class IndexWriter:
 def __init__(self,boundary:WorkspaceBoundary):
  self.boundary=boundary;self.path=boundary.resolve(".harnessforge/workspace-index.db");self._ready=False;self._init_lock=asyncio.Lock()
 @asynccontextmanager
 async def connect(self):
  async with aiosqlite.connect(self.path) as db:yield db
 async def ensure(self):
  if self._ready:return
  async with self._init_lock:
   if self._ready:return
   await self._initialize()
 async def _initialize(self):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  async with self.connect() as db:
   await db.execute("CREATE TABLE IF NOT EXISTS index_meta (id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL DEFAULT 0,last_sync TEXT)");await db.execute("CREATE TABLE IF NOT EXISTS index_files (relative_path TEXT PRIMARY KEY,size INTEGER,mime TEXT,sha256 TEXT,mtime_ns INTEGER,symbols TEXT,snippet TEXT,parser_error TEXT)");await db.execute("INSERT OR IGNORE INTO index_meta(id,version) VALUES(1,0)");await db.commit()
  self._ready=True
 async def rebuild(self,records:list[FileRecord],timestamp:str)->int:
  await self.ensure(); version=None
  async with self.connect() as db:
   await db.execute("BEGIN IMMEDIATE"); table="index_files_new_"+uuid.uuid4().hex; await db.execute(f"CREATE TABLE {table} (relative_path TEXT PRIMARY KEY,size INTEGER,mime TEXT,sha256 TEXT,mtime_ns INTEGER,symbols TEXT,snippet TEXT,parser_error TEXT)")
   try:
    await db.executemany(f"INSERT INTO {table} VALUES(?,?,?,?,?,?,?,?)",[(r.relative_path,r.size,r.mime,r.sha256,r.mtime_ns,json.dumps(r.symbols),r.snippet,r.parser_error) for r in records]);cur=await db.execute("SELECT version FROM index_meta WHERE id=1");row=await cur.fetchone();version=int(row[0])+1;await db.execute("DROP TABLE IF EXISTS index_files");await db.execute(f"ALTER TABLE {table} RENAME TO index_files");await db.execute("UPDATE index_meta SET version=?,last_sync=? WHERE id=1",(version,timestamp));await db.commit()
   except (aiosqlite.Error,OSError,ValueError,TypeError):
    await db.rollback();raise
  return version
 async def status(self)->tuple[int,str|None,int]:
  await self.ensure()
  async with self.connect() as db:
   cur=await db.execute("SELECT version,last_sync FROM index_meta WHERE id=1");meta=await cur.fetchone();cur=await db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='index_files'"); exists=(await cur.fetchone())[0]; count=0
   if exists:cur=await db.execute("SELECT COUNT(*) FROM index_files");count=int((await cur.fetchone())[0])
  return int(meta[0]),meta[1],count
 async def query(self,query:str,limit:int)->list[FileRecord]:
  await self.ensure();escaped=query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_");needle=f"%{escaped}%"
  async with self.connect() as db:
   cur=await db.execute('SELECT relative_path,size,mime,sha256,mtime_ns,symbols,snippet,parser_error FROM index_files WHERE relative_path LIKE ? ESCAPE char(92) OR symbols LIKE ? ESCAPE char(92) OR snippet LIKE ? ESCAPE char(92) LIMIT ?',(needle,needle,needle,limit)); rows=await cur.fetchall()
  return [FileRecord(relative_path=p,size=s,mime=m,sha256=h,mtime_ns=mt,symbols=json.loads(sym),snippet=sn,parser_error=err) for p,s,m,h,mt,sym,sn,err in rows]
