import json
from fastapi.testclient import TestClient
from app.main import create_app

def graph_payload():
    return {"schema_version":"1","id":"g1","name":"demo","workspace_path":".","nodes":[{"id":"s","type":"start","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}},{"id":"o","type":"output","position":{"x":1,"y":1},"data":{"config":{},"ui":{}}}],"edges":[{"id":"e","source":"s","target":"o"}],"settings":{"review_only":True,"external_dataflow_activated":False}}

def test_graph_save_and_load_are_authenticated_and_workspace_bounded(tmp_path):
    client=TestClient(create_app(session_value="test-session", workspace=tmp_path))
    response=client.post("/api/graph",json={"path":"demo.forge.json","graph":graph_payload()},headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"})
    assert response.status_code == 201
    assert json.loads((tmp_path/"demo.forge.json").read_text())["id"] == "g1"
    loaded=client.get("/api/graph/demo.forge.json",headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"})
    assert loaded.status_code == 200 and loaded.json()["name"] == "demo"

def test_graph_api_rejects_traversal_and_invalid_schema(tmp_path):
    client=TestClient(create_app(session_value="test-session", workspace=tmp_path))
    headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    assert client.post("/api/graph",json={"path":"../escape.forge.json","graph":graph_payload()},headers=headers).status_code == 400
    bad=graph_payload(); bad["nodes"]=[]
    assert client.post("/api/graph",json={"path":"bad.forge.json","graph":bad},headers=headers).status_code == 422

def test_graph_api_rejects_symlink_destination(tmp_path):
    outside=tmp_path.parent/"outside.forge.json"; outside.write_text("secret")
    (tmp_path/"alias.forge.json").symlink_to(outside)
    client=TestClient(create_app(session_value="test-session", workspace=tmp_path))
    response=client.post("/api/graph",json={"path":"alias.forge.json","graph":graph_payload()},headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"})
    assert response.status_code == 400 and outside.read_text() == "secret"


def test_imported_graph_remains_review_only(tmp_path):
    payload=graph_payload(); payload["settings"]["review_only"]=False
    client=TestClient(create_app(session_value="test-session",workspace=tmp_path)); headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    response=client.post("/api/graph",json={"path":"active.forge.json","graph":payload},headers=headers)
    assert response.status_code == 201
    assert response.json()["review_only"] is True


def test_graph_save_rejects_missing_parent_and_non_forge_extension(tmp_path):
    c=TestClient(create_app(session_value="test-session",workspace=tmp_path)); h={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    assert c.post("/api/graph",json={"path":"missing/graph.forge.json","graph":graph_payload()},headers=h).status_code==400
    assert c.post("/api/graph",json={"path":"graph.json","graph":graph_payload()},headers=h).status_code==400


def test_graph_save_rejects_oversized_graph_config(tmp_path):
    c=TestClient(create_app(session_value="test-session",workspace=tmp_path)); payload=graph_payload(); payload["nodes"][0]["data"]["config"]={"x":"a"*2000000}; r=c.post("/api/graph",json={"path":"large.forge.json","graph":payload},headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"}); assert r.status_code in {413,422}

def test_graph_generate_endpoint_creates_valid_graph(tmp_path):
    client=TestClient(create_app(session_value="test-session", workspace=tmp_path))
    headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    response=client.post("/api/graph/generate",json={"prompt":"Erstelle einen ReAct Coding Loop mit Pytest","model":"qwen2.5-coder:32b"},headers=headers)
    assert response.status_code == 200
    data=response.json()
    assert data["schema_version"] == "1"
    assert len(data["nodes"]) >= 3
    assert len(data["edges"]) >= 2
    assert any(n["type"] == "start" for n in data["nodes"])
    assert any(n["type"] == "output" for n in data["nodes"])

def test_graph_generate_creates_rag_node_and_valid_loop(tmp_path):
    client=TestClient(create_app(session_value="test-session", workspace=tmp_path))
    headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"}
    response=client.post("/api/graph/generate",json={"prompt":"RAG Query Agent with LanceDB and validation loop","model":"codestral-latest"},headers=headers)
    assert response.status_code == 200
    data=response.json()
    assert any(n["type"] == "rag" for n in data["nodes"])
    rag_node = next(n for n in data["nodes"] if n["type"] == "rag")
    assert rag_node["data"]["config"]["path"] == ".lancedb"
    assert isinstance(rag_node["data"]["config"]["vector"], list)
