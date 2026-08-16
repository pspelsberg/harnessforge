import pytest
from app.features.observability.ws_server import WebSocketCommand, WebSocketProtocolError
def test_protocol_accepts_bounded_commands():
    assert WebSocketCommand.parse({"type":"ping"}).type=="ping"
    assert WebSocketCommand.parse({"type":"run.cancel"}).type=="run.cancel"
    assert WebSocketCommand.parse({"type":"run.pause"}).type=="run.pause"
    assert WebSocketCommand.parse({"type":"run.resume"}).type=="run.resume"
def test_protocol_rejects_unknown_or_oversized_messages():
    with pytest.raises(WebSocketProtocolError): WebSocketCommand.parse({"type":"exec"})
    with pytest.raises(WebSocketProtocolError): WebSocketCommand.parse({"type":"ping","payload":"x"*300000})
