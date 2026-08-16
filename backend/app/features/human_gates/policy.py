"""Default-deny gate policy."""
from __future__ import annotations
from app.features.human_gates.contracts import GateClass,GateCreateRequest
_REQUIRED={"tool_write","git_commit","git_push","external_dataflow","mcp_call","rlm_spawn"}
class GatePolicyError(ValueError): pass
def require_gate(gate_class: GateClass)->bool:
    return gate_class in _REQUIRED
def validate_create(request: GateCreateRequest)->None:
    if not require_gate(request.gate_class): raise GatePolicyError("unknown gate class")
    if request.gate_class=="git_push" and request.preview.risk not in {"high","critical"}: raise GatePolicyError("git push requires high risk preview")
    if not request.preview.action: raise GatePolicyError("action preview is required")
