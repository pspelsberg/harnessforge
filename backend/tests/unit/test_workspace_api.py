from fastapi.testclient import TestClient
from app.main import create_app

def headers(): return {"host":"127.0.0.1","x-harnessforge-token":"test-session"}

def test_workspace_browser_lists_only_safe_markdown_files(tmp_path):
    (tmp_path/"notes.md").write_text("hello")
    (tmp_path/"secret.txt").write_text("hidden")
    (tmp_path/".env").write_text("KEY=secret")
    client=TestClient(create_app(session_value="test-session",workspace=tmp_path))
    result=client.get("/api/workspace/list",headers=headers())
    assert result.status_code==200 and result.json()["files"]==["notes.md"]

def test_workspace_browser_reads_bounded_markdown_and_blocks_escape(tmp_path):
    (tmp_path/"notes.md").write_text("hello")
    client=TestClient(create_app(session_value="test-session",workspace=tmp_path))
    assert client.get("/api/workspace/read",params={"path":"notes.md"},headers=headers()).json()["content"]=="hello"
    assert client.get("/api/workspace/read",params={"path":"../x.md"},headers=headers()).status_code==400
    assert client.get("/api/workspace/read",params={"path":"notes.txt"},headers=headers()).status_code==400

def test_workspace_browser_requires_auth(tmp_path):
    client=TestClient(create_app(session_value="test-session",workspace=tmp_path))
    assert client.get("/api/workspace/list",headers={"host":"127.0.0.1"}).status_code==401
