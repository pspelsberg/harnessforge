"""Default-deny human gate lifecycle service."""
from __future__ import annotations
from datetime import timedelta
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.human_gates.binding import action_fingerprint,new_nonce,new_request_id,now_utc
from app.features.human_gates.contracts import GateCreateRequest,GateDecision,GateRecord,GateConsumeRequest
from app.features.human_gates.policy import GatePolicyError,validate_create
from app.features.human_gates.store import HumanGateStore,GateStoreError

class HumanGateError(RuntimeError): pass

class HumanGateService:
    def __init__(self,workspace: str|Path):
        try: self.boundary=WorkspaceBoundary(workspace)
        except UnsafePathError as exc: raise HumanGateError("invalid gate workspace") from exc
        self.store=HumanGateStore(self.boundary.workspace)

    def _check_workspace(self,request: GateCreateRequest)->str:
        try: resolved=Path(request.workspace_realpath).expanduser().resolve(strict=True)
        except (OSError,RuntimeError) as exc: raise HumanGateError("invalid gate workspace") from exc
        if resolved!=self.boundary.workspace: raise HumanGateError("gate workspace mismatch")
        for target in request.preview.write_targets:
            try: self.boundary.resolve(target,must_exist=False)
            except UnsafePathError as exc: raise HumanGateError("gate write target is outside workspace") from exc
        return str(resolved)

    async def create(self,request: GateCreateRequest)->GateRecord:
        try: validate_create(request)
        except GatePolicyError as exc: raise HumanGateError("gate policy denied") from exc
        workspace=self._check_workspace(request); issued=now_utc(); expires=issued+timedelta(seconds=request.ttl_seconds)
        gate=GateRecord(request_id=new_request_id(),nonce=new_nonce(),run_id=request.run_id,node_id=request.node_id,graph_version=request.graph_version,workspace_realpath=workspace,session_id=request.session_id,gate_class=request.gate_class,action_fingerprint=action_fingerprint(request,workspace_realpath=workspace),preview=request.preview,issued_at=issued.isoformat(),expires_at=expires.isoformat(),status="pending")
        return await self.store.create(gate)

    async def get(self,request_id: str,session_id: str)->GateRecord:
        await self.store.expire(); record=await self.store.get(request_id)
        if record.session_id!=session_id: raise HumanGateError("gate is not accessible")
        return record

    async def decide(self,decision: GateDecision)->GateRecord:
        try: return await self.store.decide(decision)
        except GateStoreError as exc: raise HumanGateError("gate decision rejected") from exc

    async def consume(self,request: GateConsumeRequest)->GateRecord:
        try: return await self.store.consume(request)
        except GateStoreError as exc: raise HumanGateError("gate consumption rejected") from exc

    async def cancel_run(self,run_id: str)->int: return await self.store.cancel_run(run_id)
    async def expire(self)->int: return await self.store.expire()
