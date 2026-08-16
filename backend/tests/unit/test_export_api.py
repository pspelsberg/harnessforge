from fastapi.testclient import TestClient
from app.main import create_app
from tests.unit.test_graph_api import graph_payload
def test_export_api_requires_auth_and_writes_workspace(tmp_path):
 c=TestClient(create_app(session_value="t",workspace=tmp_path)); payload=graph_payload(); payload["settings"]["review_only"]=False; h={"host":"127.0.0.1","x-harnessforge-token":"t"}
 assert c.post("/api/export",json={"graph":payload,"destination":"bundle"},headers={"host":"127.0.0.1"}).status_code==401
 result=c.post("/api/export",json={"graph":payload,"destination":"bundle"},headers=h)
 assert result.status_code==201 and (tmp_path/"bundle"/"agent_runner.py").exists() and (tmp_path/"bundle.zip").exists()
