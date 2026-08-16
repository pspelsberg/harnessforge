from fastapi.testclient import TestClient
import pytest
from app.main import create_app

def test_websocket_requires_token_and_origin():
    app=create_app(session_value="test-session"); client=TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws", headers={"origin":"http://127.0.0.1:5173"}): pass
    with client.websocket_connect("/ws", headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173","x-harnessforge-token":"test-session"}) as ws:
        ws.send_json({"type":"ping"})
        assert ws.receive_json() == {"type":"pong"}

def test_websocket_rejects_untrusted_origin():
    app=create_app(session_value="test-session"); client=TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws", headers={"origin":"https://evil.example","x-harnessforge-token":"test-session"}): pass


def test_websocket_rejects_unknown_commands(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); client=TestClient(app)
    with client.websocket_connect("/ws",headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173","x-harnessforge-token":"test-session"}) as ws:
        ws.send_json({"type":"run.cancel"}); assert ws.receive_json()=={"type":"run.cancelled"}


def test_websocket_cancel_command_sets_active_runner_cancelled(tmp_path):
    from app.features.execution.engine import GraphRunner
    app=create_app(session_value="test-session",workspace=tmp_path); runner=GraphRunner
    app.state.active_runner=runner.__new__(runner)
    app.state.active_runner._cancelled=False
    with TestClient(app).websocket_connect("/ws",headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173","x-harnessforge-token":"test-session"}) as ws:
        ws.send_json({"type":"run.cancel"})
        assert ws.receive_json()=={"type":"run.cancelled"}
    assert app.state.active_runner._cancelled is True


def test_websocket_browser_auth_message_flow(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); client=TestClient(app)
    with client.websocket_connect("/ws",headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173"}) as ws:
        ws.send_json({"type":"auth","token":"test-session"}); assert ws.receive_json()=={"type":"authenticated"}; ws.send_json({"type":"ping"}); assert ws.receive_json()=={"type":"pong"}



def test_websocket_pause_resume_commands(tmp_path):
    app=create_app(session_value="test-session",workspace=tmp_path); from app.features.execution.engine import GraphRunner; app.state.active_runner=GraphRunner.__new__(GraphRunner); app.state.active_runner._paused=False; app.state.active_runner.event_sink=lambda event:None; app.state.active_runner._resume_event=__import__("asyncio").Event(); app.state.active_runner._resume_event.set()
    with TestClient(app).websocket_connect("/ws",headers={"host":"127.0.0.1","origin":"http://127.0.0.1:5173","x-harnessforge-token":"test-session"}) as ws:
        ws.send_json({"type":"run.pause"}); assert ws.receive_json()=={"type":"run.paused"}; ws.send_json({"type":"run.resume"}); assert ws.receive_json()=={"type":"run.resumed"}
