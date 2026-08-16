import asyncio
from fastapi.testclient import TestClient
from app.main import create_app
from app.features.observability.store import RunStore

def test_run_delete_endpoints_are_authenticated(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    assert c.delete("/api/runs/r1",headers={"host":"127.0.0.1"}).status_code==401
    assert c.delete("/api/runs/r1",headers=h).status_code in {204,404}
    assert c.delete("/api/runs",headers=h).status_code==204


def test_run_history_endpoint_requires_auth(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    assert c.get("/api/runs",headers={"host":"127.0.0.1"}).status_code==401
    assert c.get("/api/runs",headers=h).status_code==200
