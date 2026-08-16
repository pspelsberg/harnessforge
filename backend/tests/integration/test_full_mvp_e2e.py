import asyncio, json, subprocess, sys
from fastapi.testclient import TestClient
from app.main import create_app
from app.features.execution.ports import ExecutionServices
from app.features.graph_authoring.contracts import ForgeGraph,GraphNode,GraphEdge
class Provider:
 async def complete(self,request,**kwargs):
  assert "<untrusted_context>" in request.messages[0]["content"]; yield type("Chunk",(),{"text":"answer"})()
class Retrieval:
 def search(self,*args,**kwargs): return [{"text":"reference","score":.1,"metadata":{"source":"fixture"}}]
class Tool:
 async def run(self,spec,approved_hash): return type("Result",(),{"stdout":"tool-answer","stderr":"","returncode":0,"timed_out":False,"trust_mode":"local_trust_mode"})()
def graph(tmp_path):
 def n(i,t,c=None): return {"id":i,"type":t,"position":{"x":0,"y":0},"data":{"config":c or {},"ui":{}}}
 return {"schema_version":"1","id":"e2e","name":"e2e","workspace_path":".","nodes":[n("s","start"),n("r","rag",{"path":"db","table":"docs","vector":[1]}),n("l","llm",{"provider":{"kind":"local_openai","base_url":"http://127.0.0.1:8000/v1","model":"x","timeout_seconds":2},"node_prompt":"{query}"}),n("o","output")],"edges":[{"id":"1","source":"s","target":"r"},{"id":"2","source":"r","target":"l"},{"id":"3","source":"l","target":"o"}],"settings":{"review_only":False,"external_dataflow_activated":False}}
def test_full_local_mvp_e2e(tmp_path):
 (tmp_path/"db").mkdir(); app=create_app(session_value="e2e-token",workspace=tmp_path,execution_services=ExecutionServices(provider=Provider(),retrieval=Retrieval(),tool=Tool())); client=TestClient(app); headers={"host":"127.0.0.1","x-harnessforge-token":"e2e-token"}; response=client.post("/api/run",json={"graph":graph(tmp_path),"query":"hello"},headers=headers); assert response.status_code==200; run_id=response.json()["run_id"]; events=client.get(f"/api/runs/{run_id}/events",headers=headers).json()["events"]; assert events[-1]["type"]=="run.succeeded"; assert (tmp_path/".harnessforge"/"runs.db").exists(); exported=client.post("/api/export",json={"graph":graph(tmp_path),"destination":"bundle"},headers=headers); assert exported.status_code==201 and (tmp_path/"bundle.zip").exists()


def test_e2e_websocket_control_and_readiness(tmp_path):
    app=create_app(session_value="e2e-token",workspace=tmp_path); client=TestClient(app); headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173","x-harnessforge-token":"e2e-token"}
    assert client.get("/ready",headers={"host":"127.0.0.1"}).json()["localhost_only"] is True
    with client.websocket_connect("/ws",headers=headers) as ws:
        ws.send_json({"type":"ping"}); assert ws.receive_json()=={"type":"pong"}; ws.send_json({"type":"run.cancel"}); assert ws.receive_json()=={"type":"run.cancelled"}
