"""SQLite persistence with transactional, single-use gate transitions."""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import aiosqlite
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
from app.features.human_gates.contracts import GateDecision, GateRecord, GateRequest, GateStatus, GateConsumeRequest

class GateStoreError(RuntimeError): pass

class HumanGateStore:
    def __init__(self, workspace: str|Path):
        try:
            self.boundary=WorkspaceBoundary(workspace)
            self.path=self.boundary.resolve(".harnessforge/human-gates.db")
        except UnsafePathError as exc: raise GateStoreError("invalid gate workspace") from exc
        self._ready=False
    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys=ON")
            yield db
    async def initialize(self)->None:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        async with self._connect() as db:
            await db.execute("CREATE TABLE IF NOT EXISTS gates (request_id TEXT PRIMARY KEY, nonce TEXT NOT NULL UNIQUE, run_id TEXT NOT NULL, session_id TEXT NOT NULL, status TEXT NOT NULL, expires_at TEXT NOT NULL, payload TEXT NOT NULL)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_gates_run ON gates(run_id,status)")
            await db.commit()
        self._ready=True
    async def _ensure(self):
        if not self._ready: await self.initialize()
    @staticmethod
    def _parse(payload: str, status: str)->GateRecord:
        data=json.loads(payload); data["status"]=status
        return GateRecord.model_validate(data)
    async def create(self, request: GateRequest)->GateRecord:
        if request.status != "pending": raise GateStoreError("new gate must be pending")
        await self._ensure()
        try:
            async with self._connect() as db:
                await db.execute("INSERT INTO gates(request_id,nonce,run_id,session_id,status,expires_at,payload) VALUES (?,?,?,?,?,?,?)",(request.request_id,request.nonce,request.run_id,request.session_id,request.status,request.expires_at,request.model_dump_json()))
                await db.commit()
        except aiosqlite.IntegrityError as exc: raise GateStoreError("gate already exists") from exc
        return GateRecord.model_validate(request.model_dump())
    async def get(self,request_id: str)->GateRecord:
        await self._ensure()
        async with self._connect() as db:
            cursor=await db.execute("SELECT status,payload FROM gates WHERE request_id=?",(request_id,)); row=await cursor.fetchone()
        if row is None: raise GateStoreError("gate does not exist")
        try: return self._parse(row[1],row[0])
        except (ValueError,TypeError,json.JSONDecodeError) as exc: raise GateStoreError("gate record is invalid") from exc
    async def _decide(self, decision: GateDecision)->GateRecord:
        await self._ensure(); now=datetime.now(timezone.utc)
        async with self._connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor=await db.execute("SELECT status,expires_at,payload,session_id,nonce FROM gates WHERE request_id=?",(decision.request_id,)); row=await cursor.fetchone()
            if row is None: await db.rollback(); raise GateStoreError("gate does not exist")
            status,expires,payload,session_id,nonce=row
            if nonce!=decision.nonce or session_id!=decision.session_id: await db.rollback(); raise GateStoreError("gate binding mismatch")
            if status!="pending": await db.rollback(); raise GateStoreError("gate is not pending")
            try: expired=now >= datetime.fromisoformat(expires.replace("Z","+00:00"))
            except ValueError: expired=True
            if expired:
                await db.execute("UPDATE gates SET status=? WHERE request_id=?",("expired",decision.request_id)); await db.commit(); raise GateStoreError("gate has expired")
            await db.execute("UPDATE gates SET status=? WHERE request_id=? AND status='pending'",(decision.decision,decision.request_id)); await db.commit()
        return self._parse(payload,decision.decision)
    async def decide(self,decision: GateDecision)->GateRecord: return await self._decide(decision)
    async def consume(self,request: GateConsumeRequest)->GateRecord:
        await self._ensure()
        async with self._connect() as db:
            await db.execute("BEGIN IMMEDIATE")
            cursor=await db.execute("SELECT status,payload,nonce,session_id,run_id,expires_at FROM gates WHERE request_id=?",(request.request_id,)); row=await cursor.fetchone()
            if row is None: await db.rollback(); raise GateStoreError("gate does not exist")
            status,payload,nonce,session_id,run_id,expires_at=row
            try: expired=datetime.now(timezone.utc) >= datetime.fromisoformat(expires_at.replace("Z","+00:00"))
            except ValueError: expired=True
            if expired and status in {"pending","approved"}:
                await db.execute("UPDATE gates SET status='expired' WHERE request_id=?",(request.request_id,)); await db.commit(); raise GateStoreError("gate has expired")
            if status!="approved" or nonce!=request.nonce or session_id!=request.session_id or run_id!=request.run_id: await db.rollback(); raise GateStoreError("gate cannot be consumed")
            data=json.loads(payload)
            if data.get("action_fingerprint")!=request.action_fingerprint: await db.rollback(); raise GateStoreError("action binding mismatch")
            await db.execute("UPDATE gates SET status='consumed' WHERE request_id=? AND status='approved'",(request.request_id,)); await db.commit()
        return self._parse(payload,"consumed")
    async def cancel_run(self,run_id: str)->int:
        await self._ensure()
        async with self._connect() as db:
            cursor=await db.execute("UPDATE gates SET status='cancelled' WHERE run_id=? AND status IN ('pending','approved')",(run_id,)); await db.commit(); return cursor.rowcount
    async def expire(self)->int:
        await self._ensure(); now=datetime.now(timezone.utc).isoformat()
        async with self._connect() as db:
            cursor=await db.execute("UPDATE gates SET status='expired' WHERE status IN ('pending','approved') AND expires_at<=?",(now,)); await db.commit(); return cursor.rowcount
