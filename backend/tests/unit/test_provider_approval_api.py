from fastapi.testclient import TestClient
from app.main import create_app
def test_provider_approval_returns_non_secret_fingerprint(tmp_path):
    app=create_app(session_value="t",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"t"}
    payload={"provider":{"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2},"bindings":["query","last_output"]}
    r=c.post("/api/provider/approval",json=payload,headers=h); assert r.status_code==200; assert len(r.json()["approval_fingerprint"])==64; assert "key" not in r.text.lower()

def test_provider_approval_rejects_invalid_bindings_and_unauthenticated(tmp_path):
    app=create_app(session_value="t",workspace=tmp_path); c=TestClient(app); payload={"provider":{"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2},"bindings":["query",1]}
    assert c.post("/api/provider/approval",json=payload,headers={"host":"127.0.0.1"}).status_code==401
    assert c.post("/api/provider/approval",json=payload,headers={"host":"127.0.0.1","x-harnessforge-token":"t"}).status_code==400


def test_provider_approval_rejects_too_many_bindings(tmp_path):
    app=create_app(session_value="t",workspace=tmp_path); c=TestClient(app); h={"host":"127.0.0.1","x-harnessforge-token":"t"}; payload={"provider":{"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2},"bindings":["q"]*33}
    assert c.post("/api/provider/approval",json=payload,headers=h).status_code==400
