"""Private SQLite run/event persistence with explicit deletion."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timedelta, timezone
import aiosqlite
from app.features.observability.events import Event, redact_event

class RunStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON")
            yield db

    async def initialize(self, *, retention_days: int = 30):
        if not 1 <= retention_days <= 365: raise ValueError("invalid retention")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connect() as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL)")
            await db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, type TEXT NOT NULL, payload TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE)")
            await db.execute("CREATE TABLE IF NOT EXISTS checkpoints (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, step INTEGER NOT NULL, payload TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id,id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at)")
            await db.commit()
        cutoff=(datetime.now(timezone.utc)-timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
        await self.purge_before(cutoff)

    async def create_run(self, run_id: str):
        import re
        if not isinstance(run_id,str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}",run_id):
            raise ValueError("invalid run id")
        async with self._connect() as db:
            await db.execute("INSERT INTO runs VALUES (?,datetime('now'))", (run_id,))
            await db.commit()

    async def list_runs(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
        if not 1 <= limit <= 1000 or offset < 0: raise ValueError("invalid run pagination")
        async with self._connect() as db:
            cursor=await db.execute("SELECT id,created_at FROM runs ORDER BY created_at,id LIMIT ? OFFSET ?",(limit,offset)); rows=await cursor.fetchall()
        return [{"id":row[0],"created_at":row[1]} for row in rows]

    async def exists_run(self, run_id: str) -> bool:
        async with self._connect() as db:
            cursor=await db.execute("SELECT 1 FROM runs WHERE id=?",(run_id,)); return await cursor.fetchone() is not None

    async def save_checkpoint(self, run_id: str, step: int, payload: dict):
        import json
        if not isinstance(step,int) or step<0 or len(json.dumps(payload).encode())>5*1024*1024: raise ValueError("invalid checkpoint")
        async with self._connect() as db:
            await db.execute("INSERT INTO checkpoints(run_id,step,payload) VALUES (?,?,?)",(run_id,step,json.dumps(payload,separators=(",",":")))); await db.commit()
    async def list_checkpoints(self, run_id: str, *, limit: int = 1000):
        if not 1<=limit<=10000: raise ValueError("invalid checkpoint limit")
        async with self._connect() as db:
            cursor=await db.execute("SELECT step,payload FROM checkpoints WHERE run_id=? ORDER BY step LIMIT ?",(run_id,limit)); rows=await cursor.fetchall()
        import json
        return [{"step":row[0],"payload":json.loads(row[1])} for row in rows]

    async def append_event(self, run_id: str, event: Event):
        if event.run_id != run_id:
            raise ValueError("event run mismatch")
        clean = redact_event(event)
        payload = clean.model_dump_json()
        if len(payload.encode()) > 256 * 1024:
            raise ValueError("event too large")
        async with self._connect() as db:
            await db.execute("INSERT INTO events(run_id,type,payload) VALUES (?,?,?)", (run_id, clean.type, payload))
            await db.commit()

    async def list_events(self, run_id: str, *, limit: int = 1000, offset: int = 0) -> list[Event]:
        if not 1 <= limit <= 10000 or offset < 0:
            raise ValueError("invalid event pagination")
        async with self._connect() as db:
            cur = await db.execute("SELECT payload FROM events WHERE run_id=? ORDER BY id LIMIT ? OFFSET ?", (run_id, limit, offset))
            rows = await cur.fetchall()
        return [Event.model_validate_json(row[0]) for row in rows]

    async def purge_before(self, cutoff_iso: str) -> None:
        async with self._connect() as db:
            await db.execute("DELETE FROM events WHERE run_id IN (SELECT id FROM runs WHERE created_at < ?)", (cutoff_iso,))
            await db.execute("DELETE FROM checkpoints WHERE run_id IN (SELECT id FROM runs WHERE created_at < ?)", (cutoff_iso,))
            await db.execute("DELETE FROM runs WHERE created_at < ?", (cutoff_iso,))
            await db.commit()

    async def delete_run(self, run_id: str):
        async with self._connect() as db:
            await db.execute("DELETE FROM events WHERE run_id=?", (run_id,))
            await db.execute("DELETE FROM checkpoints WHERE run_id=?", (run_id,))
            await db.execute("DELETE FROM runs WHERE id=?", (run_id,))
            await db.commit()

    async def delete_all(self):
        async with self._connect() as db:
            await db.execute("DELETE FROM events")
            await db.execute("DELETE FROM checkpoints")
            await db.execute("DELETE FROM runs")
            await db.commit()
