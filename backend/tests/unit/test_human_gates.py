import asyncio
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.features.human_gates.contracts import ActionPreview,GateConsumeRequest,GateCreateRequest,GateDecision
from app.features.human_gates.service import HumanGateError,HumanGateService

def create_request(tmp_path,**overrides):
    data={"run_id":"run-1","node_id":"tool-1","graph_version":"a"*64,"workspace_realpath":str(tmp_path.resolve()),"session_id":"session-1","gate_class":"tool_write","preview":ActionPreview(action="tool.execute",command="echo safe",diff="",dataflow="local",risk="high",write_targets=["src"]),"ttl_seconds":300}; data.update(overrides); return GateCreateRequest.model_validate(data)

@pytest.mark.asyncio
async def test_gate_lifecycle_is_bound_and_single_use(tmp_path):
    service=HumanGateService(tmp_path); record=await service.create(create_request(tmp_path)); assert record.status=="pending" and record.preview.command=="echo safe"
    assert (await service.get(record.request_id,"session-1")).status=="pending"
    approved=await service.decide(GateDecision(request_id=record.request_id,nonce=record.nonce,session_id="session-1",decision="approved")); assert approved.status=="approved"
    consumed=await service.consume(GateConsumeRequest(request_id=record.request_id,nonce=record.nonce,session_id="session-1",run_id="run-1",action_fingerprint=record.action_fingerprint)); assert consumed.status=="consumed"
    with pytest.raises(HumanGateError): await service.consume(GateConsumeRequest(request_id=record.request_id,nonce=record.nonce,session_id="session-1",run_id="run-1",action_fingerprint=record.action_fingerprint))

@pytest.mark.asyncio
async def test_gate_rejects_replay_stale_binding_and_wrong_session(tmp_path):
    service=HumanGateService(tmp_path); record=await service.create(create_request(tmp_path))
    with pytest.raises(HumanGateError): await service.decide(GateDecision(request_id=record.request_id,nonce="b"*32,session_id="session-1",decision="approved"))
    with pytest.raises(HumanGateError): await service.get(record.request_id,"other-session")
    await service.decide(GateDecision(request_id=record.request_id,nonce=record.nonce,session_id="session-1",decision="approved"))
    with pytest.raises(HumanGateError): await service.consume(GateConsumeRequest(request_id=record.request_id,nonce=record.nonce,session_id="session-1",run_id="run-1",action_fingerprint="b"*64))

@pytest.mark.asyncio
async def test_gate_decision_is_race_safe_default_deny_and_cancel(tmp_path):
    service=HumanGateService(tmp_path); record=await service.create(create_request(tmp_path))
    decisions=[GateDecision(request_id=record.request_id,nonce=record.nonce,session_id="session-1",decision="approved"),GateDecision(request_id=record.request_id,nonce=record.nonce,session_id="session-1",decision="denied")]
    results=await asyncio.gather(*(service.decide(item) for item in decisions),return_exceptions=True)
    assert sum(not isinstance(item,Exception) for item in results)==1
    other=await service.create(create_request(tmp_path,run_id="run-2")); assert await service.cancel_run("run-2")==1
    with pytest.raises(HumanGateError): await service.decide(GateDecision(request_id=other.request_id,nonce=other.nonce,session_id="session-1",decision="approved"))

@pytest.mark.asyncio
async def test_gate_preview_redacts_and_workspace_is_fixed(tmp_path):
    service=HumanGateService(tmp_path); record=await service.create(create_request(tmp_path,preview=ActionPreview(action="tool.execute",command="Bearer secret",risk="critical")))
    assert "[REDACTED]" in record.preview.command
    with pytest.raises(HumanGateError): await service.create(create_request(tmp_path,workspace_realpath=str(tmp_path.parent)))
    with pytest.raises(HumanGateError): await service.create(create_request(tmp_path,preview=ActionPreview(action="tool.execute",write_targets=["../outside"])))

def test_gate_contract_rejects_bad_graph_and_secret_preview():
    with pytest.raises(ValidationError): ActionPreview(action="tool.execute",command="x\x00y")
    with pytest.raises(ValidationError): GateCreateRequest(run_id="run",node_id="node",graph_version="bad",workspace_realpath="/tmp",session_id="s",gate_class="tool_write",preview=ActionPreview(action="tool.execute"))

@pytest.mark.asyncio
async def test_gate_expiry_is_terminal(tmp_path):
    service=HumanGateService(tmp_path); record=await service.create(create_request(tmp_path,ttl_seconds=1)); await asyncio.sleep(1.05)
    with pytest.raises(HumanGateError): await service.decide(GateDecision(request_id=record.request_id,nonce=record.nonce,session_id="session-1",decision="approved"))
    assert (await service.get(record.request_id,"session-1")).status=="expired"

@pytest.mark.asyncio
async def test_approved_gate_cannot_be_consumed_after_expiry(tmp_path):
    service=HumanGateService(tmp_path); record=await service.create(create_request(tmp_path,ttl_seconds=1)); await service.decide(GateDecision(request_id=record.request_id,nonce=record.nonce,session_id="session-1",decision="approved")); await asyncio.sleep(1.05)
    with pytest.raises(HumanGateError): await service.consume(GateConsumeRequest(request_id=record.request_id,nonce=record.nonce,session_id="session-1",run_id="run-1",action_fingerprint=record.action_fingerprint))
