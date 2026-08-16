"""Time-travel service enforcing ownership, integrity and fork policy."""
from __future__ import annotations
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.core.security.redaction import redact_payload
from app.features.execution.state import AgentState
from app.features.time_travel.contracts import CreateCheckpointRequest,CheckpointView,ForkRequest,ForkResult
from app.features.time_travel.forker import ForkError,StateForker
from app.features.time_travel.lineage import state_hash
from app.features.time_travel.reader import CheckpointReader,TimeTravelReadError
from app.features.time_travel.store import TimeTravelStore,TimeTravelStoreError
import uuid
class TimeTravelError(RuntimeError): pass
class TimeTravelService:
    def __init__(self,workspace: str|Path):
        try: self.boundary=WorkspaceBoundary(workspace)
        except UnsafePathError as exc: raise TimeTravelError("invalid time-travel workspace") from exc
        self.store=TimeTravelStore(self.boundary.workspace); self.reader=CheckpointReader(self.store); self.forker=StateForker(self.store)
    def _workspace(self,value: str)->str:
        try: resolved=Path(value).resolve(strict=True)
        except (OSError,RuntimeError) as exc: raise TimeTravelError("invalid fork workspace") from exc
        if resolved!=self.boundary.workspace: raise TimeTravelError("workspace mismatch")
        return str(resolved)
    async def create_checkpoint(self,request: CreateCheckpointRequest)->CheckpointView:
        workspace=self._workspace(request.workspace_realpath)
        try: state=AgentState.model_validate(request.state)
        except ValueError as exc: raise TimeTravelError("checkpoint state invalid") from exc
        clean=redact_payload(state.model_dump(mode="json")); checkpoint=CheckpointView(checkpoint_id="cp-"+uuid.uuid4().hex,run_id=request.run_id,session_id=request.session_id,graph_version=request.graph_version,workspace_realpath=workspace,step=request.step,state_hash=state_hash(clean),state=clean)
        try: return await self.store.save_checkpoint(checkpoint)
        except TimeTravelStoreError as exc: raise TimeTravelError("checkpoint persistence failed") from exc
    async def read(self,request: ForkRequest)->CheckpointView:
        workspace=self._workspace(request.workspace_realpath)
        try: return await self.reader.read(request.checkpoint_id,session_id=request.session_id,run_id=request.run_id,graph_version=request.graph_version,workspace_realpath=workspace)
        except TimeTravelReadError as exc: raise TimeTravelError("checkpoint unavailable") from exc
    async def fork(self,request: ForkRequest)->ForkResult:
        checkpoint=await self.read(request); depth=await self.store.get_run_depth(request.run_id)
        try: return await self.forker.fork(checkpoint,request,depth)
        except ForkError as exc: raise TimeTravelError("fork rejected") from exc
