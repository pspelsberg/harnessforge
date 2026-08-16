"""Canonical action binding and replay-resistant nonce helpers."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,secrets
from app.features.human_gates.contracts import ActionPreview,GateCreateRequest

def new_nonce()->str: return secrets.token_urlsafe(24)[:32]
def new_request_id()->str: return "gate-"+secrets.token_hex(16)
def action_fingerprint(request: GateCreateRequest, *, workspace_realpath: str)->str:
    payload={"run_id":request.run_id,"node_id":request.node_id,"graph_version":request.graph_version,"workspace_realpath":workspace_realpath,"session_id":request.session_id,"gate_class":request.gate_class,"preview":request.preview.model_dump(mode="json")}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def now_utc()->datetime: return datetime.now(timezone.utc)
