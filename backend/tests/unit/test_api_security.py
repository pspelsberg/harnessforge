from fastapi.testclient import TestClient
from app.main import create_app

def test_health_is_public_but_api_requires_session_and_host():
    app=create_app(session_value="test-session")
    client=TestClient(app)
    assert client.get("/health", headers={"host":"127.0.0.1"}).status_code == 200
    assert client.get("/api/graph", headers={"host":"127.0.0.1"}).status_code == 401
    assert client.get("/api/graph", headers={"host":"127.0.0.1","x-harnessforge-token":"test-session"}).status_code == 200

def test_bad_host_and_origin_are_rejected():
    app=create_app(session_value="test-session")
    client=TestClient(app)
    assert client.get("/health", headers={"host":"evil.example"}).status_code == 400
    assert client.get("/health", headers={"host":"127.0.0.1","origin":"https://evil.example"}).status_code == 400


def test_host_userinfo_and_bad_port_are_rejected():
    app=create_app(session_value="test-session"); client=TestClient(app)
    assert client.get("/health", headers={"host":"127.0.0.1@evil.example"}).status_code == 400
    assert client.get("/health", headers={"host":"127.0.0.1:bad"}).status_code == 400


def test_invalid_responses_have_security_headers():
    app=create_app(session_value="test-session"); client=TestClient(app,raise_server_exceptions=False)
    response=client.get("/health",headers={"host":"evil.example"})
    assert response.status_code == 400 and response.headers["x-content-type-options"] == "nosniff" and "content-security-policy" in response.headers

def test_host_port_must_be_supported():
    app=create_app(session_value="test-session"); client=TestClient(app)
    assert client.get("/health",headers={"host":"127.0.0.1:9999"}).status_code == 400


def test_oversized_request_is_rejected():
    app=create_app(session_value="test-session"); client=TestClient(app)
    response=client.get("/health",headers={"host":"127.0.0.1","content-length":"999999999"})
    assert response.status_code == 413


def test_malformed_host_error_has_security_headers():
    app=create_app(session_value="test-session"); client=TestClient(app)
    response=client.get("/health",headers={"host":"127.0.0.1:bad"})
    assert response.status_code == 400 and response.headers["x-content-type-options"] == "nosniff"


def test_non_string_token_like_values_are_rejected():
    token=__import__("app.core.security.session",fromlist=["SessionToken"]).SessionToken()
    assert token.verify(None) is False and token.verify(123) is False


def test_repeated_failed_auth_is_throttled(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); client=TestClient(app)
    headers={"host":"127.0.0.1","x-harnessforge-token":"wrong"}
    responses=[client.get("/api/graph",headers=headers) for _ in range(25)]
    assert any(response.status_code==429 for response in responses)


def test_unhandled_exceptions_are_generic_and_have_security_headers():
    app=create_app(session_value="test-session");
    @app.get("/boom")
    async def boom(): raise RuntimeError("secret stack detail")
    response=TestClient(app,raise_server_exceptions=False).get("/boom",headers={"host":"127.0.0.1"})
    assert response.status_code==500 and "secret stack detail" not in response.text and response.headers["x-content-type-options"]=="nosniff"


def test_readiness_reports_local_runtime(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); response=TestClient(app).get("/ready",headers={"host":"127.0.0.1"}); assert response.status_code==200 and response.json()["status"]=="ready"


def test_auth_failures_are_counted_without_token_logging(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); client=TestClient(app); client.get("/api/graph",headers={"host":"127.0.0.1","x-harnessforge-token":"secret-token"}); assert app.state.auth_failures==1


def test_cors_is_restricted_and_credentials_disabled(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); c=TestClient(app); r=c.options("/health",headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173","access-control-request-method":"GET"}); assert r.headers.get("access-control-allow-origin")=="http://127.0.0.1:5173" and "true" not in r.headers.get("access-control-allow-credentials","").lower()


def test_readiness_has_security_headers(tmp_path):
 r=TestClient(create_app(session_value="t",workspace=tmp_path)).get("/ready",headers={"host":"127.0.0.1"}); assert r.headers["x-content-type-options"]=="nosniff" and "frame-ancestors" in r.headers["content-security-policy"]
