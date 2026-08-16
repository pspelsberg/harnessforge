from fastapi.testclient import TestClient
from app.main import create_app
from tests.unit.test_graph_api import graph_payload

def test_run_requires_authenticated_activated_graph(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    blocked=c.post("/api/run",json={"graph":graph_payload(),"query":"hello"},headers=h)
    assert blocked.status_code == 409
    payload=graph_payload(); payload["settings"]["review_only"]=False
    ok=c.post("/api/run",json={"graph":payload,"query":"hello"},headers=h)
    assert ok.status_code == 200 and ok.json()["status"] == "succeeded"

def test_run_rejects_oversized_query(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    payload=graph_payload(); payload["settings"]["review_only"]=False
    assert c.post("/api/run",json={"graph":payload,"query":"x"*200000},headers=h).status_code == 413


def test_run_api_rejects_unconfigured_service_nodes(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    payload=graph_payload(); payload["settings"]["review_only"]=False; payload["nodes"][0]={"id":"s","type":"start","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}}; payload["nodes"].insert(1,{"id":"l","type":"llm","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}}); payload["edges"]=[{"id":"1","source":"s","target":"l"},{"id":"2","source":"l","target":"o"}]
    result=c.post("/api/run",json={"graph":payload,"query":"x"},headers=h)
    assert result.status_code==400 and "provider" in result.json()["detail"]


def test_run_api_accepts_injected_execution_services(tmp_path):
    from app.features.execution.ports import ExecutionServices
    class Provider:
        async def complete(self,request,**kwargs):
            yield type("Chunk",(),{"text":"ok"})()
    from fastapi.testclient import TestClient
    app=create_app(session_value="test-session",workspace=tmp_path,execution_services=ExecutionServices(provider=Provider())); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    payload=graph_payload(); payload["settings"]["review_only"]=False; payload["nodes"][0]={"id":"s","type":"start","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}}; payload["nodes"].insert(1,{"id":"l","type":"llm","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}}); payload["edges"]=[{"id":"1","source":"s","target":"l"},{"id":"2","source":"l","target":"o"}]
    assert c.post("/api/run",json={"graph":payload,"query":"x"},headers=h).json()["status"]=="succeeded"


def test_run_api_returns_controlled_failure_for_tool_node(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    payload=graph_payload(); payload["settings"]["review_only"]=False; payload["nodes"].insert(1,{"id":"t","type":"tool","position":{"x":0,"y":0},"data":{"config":{"path":"missing.py","args":[]},"ui":{}}}); payload["edges"]=[{"id":"1","source":"s","target":"t"},{"id":"2","source":"t","target":"o"}]
    result=c.post("/api/run",json={"graph":payload,"query":"x"},headers=h); assert result.status_code==400 and "tool" in result.json()["detail"]


def test_run_api_persists_lifecycle_events(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    payload=graph_payload(); payload["settings"]["review_only"]=False
    response=c.post("/api/run",json={"graph":payload,"query":"hello"},headers=h)
    assert response.status_code==200 and isinstance(response.json()["run_id"],str)
    events=c.get(f"/api/runs/{response.json()['run_id']}/events",headers=h).json()["events"]
    assert events[0]["type"]=="run.created" and events[1]["type"]=="run.validating" and events[-1]["type"]=="run.succeeded"


def test_run_api_rejects_when_process_run_is_active(tmp_path):
    from app.features.execution.engine import GraphRunner
    app=create_app(session_value="test-session",workspace=tmp_path); GraphRunner._active=True; c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}; payload=graph_payload(); payload["settings"]["review_only"]=False
    try: assert c.post("/api/run",json={"graph":payload,"query":"x"},headers=h).status_code==400
    finally: GraphRunner._active=False


def test_run_response_has_bounded_state_and_no_secret_config(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}; payload=graph_payload(); payload["settings"]["review_only"]=False
    r=c.post("/api/run",json={"graph":payload,"query":"hello"},headers=h); assert r.status_code==200 and "OPENAI_API_KEY" not in r.text
