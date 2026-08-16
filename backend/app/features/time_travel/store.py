"""SQLite persistence for immutable checkpoint and fork records."""
from __future__ import annotations
from contextlib import asynccontextmanager
import asyncio
import json
from pathlib import Path
import aiosqlite
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.time_travel.contracts import CheckpointView,ForkLineage

class TimeTravelStoreError(RuntimeError): pass
class TimeTravelStore:
    def __init__(self,workspace: str|Path):
        try: self.boundary=WorkspaceBoundary(workspace); self.path=self.boundary.resolve(".harnessforge/time-travel.db")
        except UnsafePathError as exc: raise TimeTravelStoreError("invalid time-travel workspace") from exc
        self._ready=False
        self._init_lock=asyncio.Lock()
    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON"); yield db
    async def initialize(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        async with self._connect() as db:
            await db.execute("CREATE TABLE IF NOT EXISTS checkpoints (checkpoint_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, session_id TEXT NOT NULL, graph_version TEXT NOT NULL, workspace_realpath TEXT NOT NULL, step INTEGER NOT NULL, state_hash TEXT NOT NULL, payload TEXT NOT NULL)")
            await db.execute("CREATE TABLE IF NOT EXISTS forks (fork_run_id TEXT PRIMARY KEY, parent_run_id TEXT NOT NULL, checkpoint_id TEXT NOT NULL, session_id TEXT NOT NULL, lineage_depth INTEGER NOT NULL, payload TEXT NOT NULL, FOREIGN KEY(checkpoint_id) REFERENCES checkpoints(checkpoint_id))")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tt_checkpoints_run ON checkpoints(run_id,step)")
            await db.commit()
        self._ready=True
    async def _ensure(self):
        if self._ready: return
        async with self._init_lock:
            if not self._ready: await self.initialize()
    async def save_checkpoint(self,checkpoint: CheckpointView)->CheckpointView:
        await self._ensure()
        try:
            async with self._connect() as db:
                await db.execute("INSERT INTO checkpoints(checkpoint_id,run_id,session_id,graph_version,workspace_realpath,step,state_hash,payload) VALUES (?,?,?,?,?,?,?,?)",(checkpoint.checkpoint_id,checkpoint.run_id,checkpoint.session_id,checkpoint.graph_version,checkpoint.workspace_realpath,checkpoint.step,checkpoint.state_hash,checkpoint.model_dump_json()))
                await db.commit()
        except aiosqlite.IntegrityError as exc: raise TimeTravelStoreError("checkpoint already exists") from exc
        return checkpoint
    async def get_checkpoint(self,checkpoint_id: str)->CheckpointView:
        await self._ensure()
        async with self._connect() as db:
            cursor=await db.execute("SELECT payload FROM checkpoints WHERE checkpoint_id=?",(checkpoint_id,)); row=await cursor.fetchone()
        if row is None: raise TimeTravelStoreError("checkpoint does not exist")
        try: return CheckpointView.model_validate_json(row[0])
        except ValueError as exc: raise TimeTravelStoreError("checkpoint is invalid") from exc
    async def count_forks(self,parent_run_id: str)->int:
        await self._ensure()
        async with self._connect() as db:
            cursor=await db.execute("SELECT COUNT(*) FROM forks WHERE parent_run_id=?",(parent_run_id,)); row=await cursor.fetchone(); return int(row[0])
    async def get_run_depth(self,run_id: str)->int:
        await self._ensure()
        async with self._connect() as db:
            cursor=await db.execute("SELECT lineage_depth FROM forks WHERE fork_run_id=?",(run_id,)); row=await cursor.fetchone()
        return int(row[0]) if row else 0

    async def save_fork(self,lineage: ForkLineage,session_id: str,state: dict)->ForkLineage:
        await self._ensure()
        async with self._connect() as db:
            try:
                await db.execute("INSERT INTO forks(fork_run_id,parent_run_id,checkpoint_id,session_id,lineage_depth,payload) VALUES (?,?,?,?,?,?)",(lineage.fork_run_id,lineage.parent_run_id,lineage.checkpoint_id,session_id,lineage.depth,json.dumps({"lineage":lineage.model_dump(mode="json"),"state":state},ensure_ascii=False,separators=(",",":"))))
                await db.commit()
            except aiosqlite.IntegrityError as exc: raise TimeTravelStoreError("fork already exists") from exc
        return lineage
