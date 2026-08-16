import hashlib,json
from pathlib import Path
import pytest
from app.features.coding_harness.contracts import AdvanceRequest,HarnessImport,HarnessTemplate,StepPolicy
from app.features.coding_harness.service import CodingHarnessService
from app.features.continual_refiner.contracts import AnalyzeRequest,ApplyRequest,Patch,Trajectory,RollbackRequest
from app.features.continual_refiner.service import RefinerService
from app.features.human_gates.contracts import ActionPreview,GateConsumeRequest,GateCreateRequest,GateDecision
from app.features.human_gates.service import HumanGateService
from app.features.time_travel.contracts import CreateCheckpointRequest,ForkRequest
from app.features.time_travel.service import TimeTravelService
from app.features.workspace_indexer.service import WorkspaceIndexService
from app.features.execution.state import AgentState

def harness_import():
 step=StepPolicy(step_id="inspect",action="inspect",capabilities=["workspace_read"]);draft=HarnessTemplate(template_id="e2e",version="1.0.0",content_hash="0"*64,signature="pending",capabilities=["workspace_read"],steps=[step],description="e2e");data=draft.model_dump(mode="json");data.pop("content_hash");data.pop("signature");digest=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest();return HarnessImport(template=draft.model_copy(update={"content_hash":digest,"signature":"local:"+digest}))

@pytest.mark.asyncio
async def test_phase2_release_flow_index_plan_checkpoint_refine_and_rollback(tmp_path):
 (tmp_path/"agents.md").write_text("old");session="session-e2e";workspace=str(tmp_path.resolve()); gates=HumanGateService(tmp_path)
 indexed=await WorkspaceIndexService(tmp_path).rebuild(session,workspace);assert indexed.indexed_files>=1
 harness=CodingHarnessService(tmp_path,gates);harness.import_template(harness_import());plan=harness.plan("e2e",session,workspace);plan,artifact=await harness.advance(AdvanceRequest(plan_id=plan.plan_id,session_id=session));assert artifact.status=="succeeded"
 state=AgentState(query="release",last_output="safe").model_dump(mode="json");travel=TimeTravelService(tmp_path);checkpoint=await travel.create_checkpoint(CreateCheckpointRequest(run_id="run-e2e",session_id=session,graph_version="a"*64,workspace_realpath=workspace,step=1,state=state));fork=await travel.fork(ForkRequest(checkpoint_id=checkpoint.checkpoint_id,run_id="run-e2e",session_id=session,graph_version="a"*64,workspace_realpath=workspace));assert fork.lineage.approvals_reissued
 old="old";patch=Patch(patch_id="patch",suggestion_id="candidate",path="agents.md",operation="replace",expected_hash=hashlib.sha256(old.encode()).hexdigest(),old_text=old,new_text="new",diff="old -> new");refiner=RefinerService(tmp_path,gates);analysis=await refiner.analyze(AnalyzeRequest(trajectory=Trajectory(run_id="run-e2e",session_id=session,workspace_realpath=workspace,events=[{"type":"failed","message":"untrusted"}]),candidate_patch=patch));suggestion=analysis.suggestions[0];preview=ActionPreview(action="refiner.apply",command=f"refiner:{suggestion.suggestion_id}:"+hashlib.sha256(json.dumps({"path":suggestion.patch.path,"expected_hash":suggestion.patch.expected_hash,"old_text":suggestion.patch.old_text,"new_text":suggestion.patch.new_text},ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest(),diff=patch.diff,risk="high",write_targets=["agents.md"]);gate=await gates.create(GateCreateRequest(run_id="run-e2e",node_id="refiner",graph_version="a"*64,workspace_realpath=workspace,session_id=session,gate_class="tool_write",preview=preview));await gates.decide(GateDecision(request_id=gate.request_id,nonce=gate.nonce,session_id=session,decision="approved"));await refiner.apply(ApplyRequest(suggestion_id=suggestion.suggestion_id,session_id=session,run_id="run-e2e",request_id=gate.request_id,nonce=gate.nonce,action_fingerprint=gate.action_fingerprint));assert (tmp_path/"agents.md").read_text()=="new";await refiner.rollback(RollbackRequest(suggestion_id=suggestion.suggestion_id,session_id=session,expected_hash=hashlib.sha256(b"new").hexdigest()));assert (tmp_path/"agents.md").read_text()=="old"


@pytest.mark.asyncio
async def test_phase2_release_security_controls_cancellation_expiry_mcp_rlm_and_repl(tmp_path):
 from pydantic import ValidationError
 from app.features.mcp_gateway.registry import McpRegistry
 from app.features.mcp_gateway.proxy import McpGateway
 from app.features.mcp_gateway.contracts import McpCallRequest
 from app.features.rlm.contracts import ChildAgentSpec
 from app.core.extension_contracts import ContextEnvelope
 from app.features.repl_sandbox.runner import ReplSessionManager
 from app.features.repl_sandbox.contracts import ReplExecuteRequest
 gates=HumanGateService(tmp_path);workspace=str(tmp_path.resolve()); preview=ActionPreview(action="tool.execute",risk="high")
 cancelled=await gates.create(GateCreateRequest(run_id="cancel-run",node_id="n",graph_version="a"*64,workspace_realpath=workspace,session_id="s",gate_class="tool_write",preview=preview));assert await gates.cancel_run("cancel-run")==1
 with pytest.raises(Exception):await gates.decide(GateDecision(request_id=cancelled.request_id,nonce=cancelled.nonce,session_id="s",decision="approved"))
 expired=await gates.create(GateCreateRequest(run_id="expire-run",node_id="n",graph_version="a"*64,workspace_realpath=workspace,session_id="s",gate_class="tool_write",preview=preview,ttl_seconds=1));import asyncio;await asyncio.sleep(1.05)
 with pytest.raises(Exception):await gates.decide(GateDecision(request_id=expired.request_id,nonce=expired.nonce,session_id="s",decision="approved"))
 mcp=McpGateway(McpRegistry(tmp_path));denied=await mcp.call_tool(McpCallRequest(run_id="r",server_id="missing",tool_name="tool"));assert denied.error_code=="mcp.unknown_server"
 with pytest.raises(ValidationError):ChildAgentSpec(run_id="r",parent_run_id="r",provider="local",prompt="x",context=ContextEnvelope(source="untrusted",origin="x",bindings=[],content={}),depth=4)
 repl=ReplSessionManager(tmp_path);sid=(await repl.create()).session_id;limited=await repl.execute(sid,ReplExecuteRequest(code="print('x'*70000)",input_data={}));assert limited.error_code=="repl.output_limit";await repl.close_all()
