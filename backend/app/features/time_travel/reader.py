"""Read-only checkpoint projection with ownership/workspace checks."""
from __future__ import annotations
from pathlib import Path
from app.features.time_travel.contracts import CheckpointView
from app.features.time_travel.store import TimeTravelStore,TimeTravelStoreError
from app.features.time_travel.lineage import state_hash
class TimeTravelReadError(RuntimeError): pass
class CheckpointReader:
    def __init__(self,store: TimeTravelStore): self.store=store
    async def read(self,checkpoint_id: str,*,session_id: str,run_id: str,graph_version: str,workspace_realpath: str)->CheckpointView:
        try: checkpoint=await self.store.get_checkpoint(checkpoint_id)
        except TimeTravelStoreError as exc: raise TimeTravelReadError("checkpoint unavailable") from exc
        if checkpoint.session_id!=session_id or checkpoint.run_id!=run_id or checkpoint.graph_version!=graph_version or checkpoint.workspace_realpath!=workspace_realpath: raise TimeTravelReadError("checkpoint binding mismatch")
        if state_hash(checkpoint.state)!=checkpoint.state_hash: raise TimeTravelReadError("checkpoint integrity failure")
        return checkpoint
