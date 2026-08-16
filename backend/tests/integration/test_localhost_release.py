import asyncio, json, subprocess, sys
from fastapi.testclient import TestClient
from app.main import create_app
from app.features.execution.ports import ExecutionServices
from app.features.graph_authoring.contracts import ForgeGraph,GraphNode,GraphEdge

def node(i,t,c=None):return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
class Provider:
 async def complete(self,request,**kwargs): yield type("Chunk",(),{"text":"ok"})()
def payload():return {"schema_version":"1","id":"g","name":"g","workspace_path":".","nodes":[{"id":"s","type":"start","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}},{"id":"o","type":"output","position":{"x":0,"y":0},"data":{"config":{},"ui":{}}}],"edges":[{"id":"e","source":"s","target":"o"}],"settings":{"review_only":False,"external_dataflow_activated":False}}
def test_localhost_api_run_event_export_release(tmp_path):
 app=create_app(session_value="release-token",workspace=tmp_path,execution_services=ExecutionServices()); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"release-token"}; r=c.post("/api/run",json={"graph":payload(),"query":"release"},headers=h); assert r.status_code==200; rid=r.json()["run_id"]; assert c.get(f"/api/runs/{rid}/events",headers=h).json()["events"][-1]["type"]=="run.succeeded"; e=c.post("/api/export",json={"graph":payload(),"destination":"bundle"},headers=h); assert e.status_code==201 and (tmp_path/"bundle.zip").exists()
