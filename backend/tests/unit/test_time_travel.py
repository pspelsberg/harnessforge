import pytest
from app.features.execution.state import AgentState
from app.features.time_travel.contracts import CreateCheckpointRequest,ForkRequest
from app.features.time_travel.service import TimeTravelError,TimeTravelService

def cp_request(tmp_path,**overrides):
    data={"run_id":"run-1","session_id":"session-1","graph_version":"a"*64,"workspace_realpath":str(tmp_path.resolve()),"step":2,"state":AgentState(query="hello",last_output="before",iteration=1).model_dump(mode="json")}; data.update(overrides); return CreateCheckpointRequest.model_validate(data)
def fork_request(tmp_path,checkpoint_id,**overrides):
    data={"checkpoint_id":checkpoint_id,"run_id":"run-1","session_id":"session-1","graph_version":"a"*64,"workspace_realpath":str(tmp_path.resolve()),"reducers":[{"op":"SET","target":"last_output","value":"after"}],"simulate_external":True}; data.update(overrides); return ForkRequest.model_validate(data)

@pytest.mark.asyncio
async def test_checkpoint_is_immutable_and_fork_applies_only_valid_reducers(tmp_path):
    service=TimeTravelService(tmp_path); checkpoint=await service.create_checkpoint(cp_request(tmp_path)); read=await service.read(fork_request(tmp_path,checkpoint.checkpoint_id)); assert read.state["last_output"]=="before"
    fork=await service.fork(fork_request(tmp_path,checkpoint.checkpoint_id)); assert fork.state["last_output"]=="after" and fork.lineage.approvals_reissued and fork.required_new_approvals==[]
    assert (await service.read(fork_request(tmp_path,checkpoint.checkpoint_id))).state["last_output"]=="before"

@pytest.mark.asyncio
async def test_time_travel_rejects_idor_stale_graph_workspace_and_approval_reuse(tmp_path):
    service=TimeTravelService(tmp_path); checkpoint=await service.create_checkpoint(cp_request(tmp_path))
    with pytest.raises(TimeTravelError): await service.read(fork_request(tmp_path,checkpoint.checkpoint_id,session_id="other"))
    with pytest.raises(TimeTravelError): await service.read(fork_request(tmp_path,checkpoint.checkpoint_id,graph_version="b"*64))
    with pytest.raises(TimeTravelError): await service.read(fork_request(tmp_path,checkpoint.checkpoint_id,workspace_realpath=str(tmp_path.parent)))
    fork=await service.fork(fork_request(tmp_path,checkpoint.checkpoint_id,simulate_external=False)); assert fork.lineage.external_actions=="approval_required" and set(fork.required_new_approvals)=={"external_provider","tool","mcp"}

@pytest.mark.asyncio
async def test_time_travel_rejects_state_poisoning_and_integrity_tamper(tmp_path):
    service=TimeTravelService(tmp_path); checkpoint=await service.create_checkpoint(cp_request(tmp_path))
    with pytest.raises(Exception): await service.fork(fork_request(tmp_path,checkpoint.checkpoint_id,reducers=[{"op":"SET","target":"metadata.__class__","value":"bad"}]))
    # Direct DB tampering is detected by the stored state hash.
    async with service.store._connect() as db:
        await db.execute("UPDATE checkpoints SET payload=json_set(payload,'$.state.last_output','tampered') WHERE checkpoint_id=?",(checkpoint.checkpoint_id,)); await db.commit()
    with pytest.raises(TimeTravelError): await service.read(fork_request(tmp_path,checkpoint.checkpoint_id))
    with pytest.raises(TimeTravelError): await service.fork(fork_request(tmp_path,checkpoint.checkpoint_id))
