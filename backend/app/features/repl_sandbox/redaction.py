"""Privacy boundary for REPL results."""
from __future__ import annotations
from app.core.security.redaction import redact_payload
from app.features.repl_sandbox.contracts import ReplResult

def redact_repl_result(result: ReplResult) -> ReplResult:
    data=result.model_dump(mode="python")
    data["stdout"]=redact_payload(data["stdout"])
    data["result"]=redact_payload(data["result"])
    return ReplResult.model_validate(data)
