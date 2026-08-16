import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app

def test_get_provider_settings_is_authenticated_and_masks_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-1234567890abcdef")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-abcdef123456")
    client = TestClient(create_app(session_value="test-session", workspace=tmp_path))
    headers = {"host": "127.0.0.1", "x-harnessforge-token": "test-session"}

    res = client.get("/api/settings/providers", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["openai"]["configured"] is True
    assert data["openai"]["masked"] == "sk-1...cdef"
    assert "sk-1234567890abcdef" not in res.text
    assert data["openrouter"]["configured"] is True
    assert data["openrouter"]["masked"] == "sk-o...3456"

def test_update_provider_settings_writes_to_workspace_env_with_0600_permissions(tmp_path, monkeypatch):
    client = TestClient(create_app(session_value="test-session", workspace=tmp_path))
    headers = {"host": "127.0.0.1", "x-harnessforge-token": "test-session"}

    res = client.post(
        "/api/settings/providers",
        json={"openai_api_key": "sk-new-openai-key-12345", "anthropic_api_key": "sk-ant-test-999", "mistral_api_key": "mistral-secret-key-123"},
        headers=headers,
    )
    assert res.status_code == 200
    env_file = tmp_path / ".env"
    assert env_file.exists()
    mode = oct(env_file.stat().st_mode & 0o777)
    assert mode == "0o600"
    content = env_file.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-new-openai-key-12345" in content
    assert "ANTHROPIC_API_KEY=sk-ant-test-999" in content
    assert "MISTRAL_API_KEY=mistral-secret-key-123" in content
    assert os.environ.get("OPENAI_API_KEY") == "sk-new-openai-key-12345"
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test-999"
    assert os.environ.get("MISTRAL_API_KEY") == "mistral-secret-key-123"

def test_update_provider_settings_rejects_non_local_ollama_url(tmp_path):
    client = TestClient(create_app(session_value="test-session", workspace=tmp_path))
    headers = {"host": "127.0.0.1", "x-harnessforge-token": "test-session"}

    res = client.post(
        "/api/settings/providers",
        json={"ollama_url": "http://evil-external-host.com/api"},
        headers=headers,
    )
    assert res.status_code == 400
