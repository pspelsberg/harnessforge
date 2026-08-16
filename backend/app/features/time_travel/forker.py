"""Controlled AgentState reducer application for new fork runs."""
from __future__ import annotations
from app.core.extension_contracts import EXTENSION_POLICY
from app.core.security.redaction import redact_payload
from app.features.execution.public import AgentState,StateLimitError,apply_reducer
from app.features.time_travel.contracts import CheckpointView,ForkRequest,ForkLineage,ForkResult
from app.features.time_travel.lineage import state_hash
from app.features.time_travel.store import TimeTravelStore,TimeTravelStoreError
import uuid
class ForkError(RuntimeError): pass
class StateForker:
    def __init__(self,store: TimeTravelStore): self.store=store
    async def fork(self,checkpoint: CheckpointView,request: ForkRequest,parent_depth: int=0)->ForkResult:
        if request.checkpoint_id!=checkpoint.checkpoint_id or request.run_id!=checkpoint.run_id or request.session_id!=checkpoint.session_id or request.graph_version!=checkpoint.graph_version or request.workspace_realpath!=checkpoint.workspace_realpath: raise ForkError("fork binding mismatch")
        if parent_depth+1>EXTENSION_POLICY.max_fork_depth: raise ForkError("fork depth exceeded")
        if await self.store.count_forks(request.run_id)>=EXTENSION_POLICY.max_forks_per_run: raise ForkError("fork count exceeded")
        if state_hash(checkpoint.state)!=checkpoint.state_hash: raise ForkError("checkpoint integrity failure")
        try: state=AgentState.model_validate(checkpoint.state)
        except ValueError as exc: raise ForkError("checkpoint state invalid") from exc
        try:
            for reducer in request.reducers: apply_reducer(state,reducer)
        except (ValueError,TypeError,StateLimitError) as exc: raise ForkError("fork state mutation rejected") from exc
        clean=redact_payload(state.model_dump(mode="json")); fork_id="fork-"+uuid.uuid4().hex
        lineage=ForkLineage(fork_run_id=fork_id,parent_run_id=request.run_id,checkpoint_id=checkpoint.checkpoint_id,graph_version=request.graph_version,workspace_realpath=request.workspace_realpath,depth=parent_depth+1,approvals_reissued=True,external_actions="simulated" if request.simulate_external else "approval_required")
        try: await self.store.save_fork(lineage,request.session_id,clean)
        except TimeTravelStoreError as exc: raise ForkError("fork persistence failed") from exc
        required=[] if request.simulate_external else ["external_provider","tool","mcp"]
        return ForkResult(lineage=lineage,state=clean,required_new_approvals=required)
