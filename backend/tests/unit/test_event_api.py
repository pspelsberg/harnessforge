from fastapi.testclient import TestClient
from app.main import create_app
def test_event_api_auth_and_validation(tmp_path):
 c=TestClient(create_app(session_value="t",workspace=tmp_path)); h={"host":"127.0.0.1","x-harnessforge-token":"t"}
 assert c.post("/api/runs/r1/events",json={"type":"run.started","payload":{}},headers={"host":"127.0.0.1"}).status_code==401
 assert c.post("/api/runs/r1/events",json={"type":"run.started","payload":{}},headers=h).status_code==201
 assert c.get("/api/runs/r1/events",headers=h).status_code==200


def test_checkpoint_api_requires_auth(tmp_path):
 c=TestClient(create_app(session_value="t",workspace=tmp_path)); h={"host":"127.0.0.1","x-harnessforge-token":"t"}
 assert c.post("/api/runs/r/checkpoints",json={"step":1,"payload":{"x":1}},headers={"host":"127.0.0.1"}).status_code==401
 assert c.post("/api/runs/r/checkpoints",json={"step":1,"payload":{"x":1}},headers=h).status_code==201
 assert c.get("/api/runs/r/checkpoints",headers=h).json()["checkpoints"][0]["step"]==1
