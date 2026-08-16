import asyncio
import pytest
from app.features.repl_sandbox.contracts import ReplExecuteRequest, ReplStatus
from app.features.repl_sandbox.policy import ReplPolicyError, validate_code
from app.features.repl_sandbox.runner import ReplError, ReplSessionManager
from app.features.repl_sandbox.events import repl_event

def test_policy_rejects_imports_filesystem_and_private_attributes():
    for code in ["import os", "import socket", "open('x')", "__import__('os')", "getattr(input_data, 'x')", "input_data.__class__"]:
        with pytest.raises(ReplPolicyError): validate_code(code)
    validate_code("result = [x * 2 for x in input_data['values']]")

def test_repl_rejects_invalid_workspace(tmp_path):
    with pytest.raises(ReplError): ReplSessionManager(tmp_path / "missing")
    with pytest.raises(ReplError): ReplSessionManager("/etc")


def test_repl_event_factory_is_versioned_and_bounded():
    event=repl_event("repl-1","repl.failed",phase="failed",error_code="repl.execution_failed",payload={"token":"secret"})
    assert event.namespace=="repl_sandbox" and event.payload["token"]=="[REDACTED]"

@pytest.mark.asyncio
async def test_persistent_session_executes_json_state_and_is_local_trust(tmp_path):
    manager=ReplSessionManager(tmp_path); info=await manager.create()
    try:
        first=await manager.execute(info.session_id,ReplExecuteRequest(code="result = input_data['value'] + 1",input_data={"value":2}))
        assert first.status==ReplStatus.SUCCEEDED and first.result==3 and first.trust_mode=="local_trust"
        second=await manager.execute(info.session_id,ReplExecuteRequest(code="result = result + 2"))
        assert second.status==ReplStatus.SUCCEEDED and second.result==5
    finally: await manager.close_all()

@pytest.mark.asyncio
async def test_repl_rejects_policy_and_cleans_session(tmp_path):
    manager=ReplSessionManager(tmp_path); info=await manager.create()
    result=await manager.execute(info.session_id,ReplExecuteRequest(code="import os"))
    assert result.status==ReplStatus.FAILED and result.error_code=="repl.policy_denied"
    await manager.interrupt(info.session_id)
    with pytest.raises(ReplError): await manager.execute(info.session_id,ReplExecuteRequest(code="result=1"))

@pytest.mark.asyncio
async def test_repl_caps_output_and_does_not_return_tracebacks(tmp_path):
    manager=ReplSessionManager(tmp_path); info=await manager.create()
    try:
        result=await manager.execute(info.session_id,ReplExecuteRequest(code="print('x' * 100000)"))
        assert result.status==ReplStatus.LIMITED and result.error_code=="repl.output_limit"
        failed=await manager.execute(info.session_id,ReplExecuteRequest(code="result = 1 / 0"))
        assert failed.status==ReplStatus.FAILED and failed.error_code=="repl.execution_failed" and failed.stdout==""
    finally: await manager.close_all()


def test_repl_api_is_authenticated_and_bounded(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    app=create_app(session_value="test-session",workspace=tmp_path)
    with TestClient(app,base_url="http://127.0.0.1:8000") as client:
        headers={"x-harnessforge-token":"test-session","origin":"http://127.0.0.1:5173"}
        denied=client.post("/api/repl/sessions",headers={"origin":"http://127.0.0.1:5173"})
        assert denied.status_code==401
        created=client.post("/api/repl/sessions",headers=headers)
        assert created.status_code==201
        session_id=created.json()["session_id"]
        result=client.post(f"/api/repl/sessions/{session_id}/execute",headers=headers,json={"code":"result = 2 + 3"})
        assert result.status_code==200 and result.json()["result"]==5
        closed=client.post(f"/api/repl/sessions/{session_id}/interrupt",headers=headers)
        assert closed.status_code==200 and closed.json()["status"]=="closed"
