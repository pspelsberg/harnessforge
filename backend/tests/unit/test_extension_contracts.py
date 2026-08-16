import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.core.extension_contracts import (
    ApprovalDecision, ApprovalRequest, CapabilityDescriptor, ContextEnvelope,
    ExtensionEvent, ExtensionPolicy, ForkRef, CheckpointRef, EXTENSION_POLICY,
)


def _approval(**overrides):
    now=datetime.now(timezone.utc)
    data={
        "request_id":"approval-1", "nonce":"a"*32, "run_id":"run-1",
        "node_id":"node-1", "action":"tool.execute",
        "action_fingerprint":"a"*64, "workspace_realpath":"/tmp/workspace",
        "issued_at":now, "expires_at":now+timedelta(seconds=60),
    }
    data.update(overrides)
    return ApprovalRequest.model_validate(data)


def test_extension_policy_is_immutable_and_bounded():
    assert EXTENSION_POLICY.max_rlm_depth == 3
    with pytest.raises(ValidationError):
        ExtensionPolicy(max_rlm_depth=4)
    with pytest.raises(ValidationError):
        EXTENSION_POLICY.max_rlm_depth = 2


def test_context_envelope_accepts_json_and_enforces_size():
    envelope=ContextEnvelope(source="untrusted", origin="rag", bindings=["query"], content={"text":"reference"})
    assert envelope.source == "untrusted"
    with pytest.raises(ValidationError):
        ContextEnvelope(source="untrusted", origin="rag", bindings=["query"], content="x"*(EXTENSION_POLICY.max_context_bytes+1))


def test_context_envelope_rejects_non_json_and_invalid_bindings():
    with pytest.raises(ValidationError):
        ContextEnvelope(source="untrusted", origin="rag", bindings=["bad path"], content={})
    with pytest.raises(ValidationError):
        ContextEnvelope(source="untrusted", origin="rag", bindings=["query"], content=object())


def test_approval_is_time_bounded_and_decision_is_strict():
    with pytest.raises(ValidationError):
        _approval(expires_at=datetime.now(timezone.utc)+timedelta(seconds=EXTENSION_POLICY.max_approval_ttl_seconds+1))
    decision=ApprovalDecision(request_id="approval-1",nonce="a"*32,decision="denied",decided_at=datetime.now(timezone.utc),reason="not now")
    assert decision.decision == "denied"


def test_approval_rejects_unsafe_workspace_realpaths():
    with pytest.raises(ValidationError): _approval(workspace_realpath="relative/workspace")
    with pytest.raises(ValidationError): _approval(workspace_realpath="/tmp/../workspace")
    with pytest.raises(ValidationError): _approval(workspace_realpath="/tmp/\x00workspace")


def test_approval_rejects_replay_shaped_or_malformed_fingerprints():
    with pytest.raises(ValidationError): _approval(nonce="short")
    with pytest.raises(ValidationError): _approval(action_fingerprint="not-a-sha256")


def test_checkpoint_and_fork_refs_are_bounded():
    now=datetime.now(timezone.utc)
    checkpoint=CheckpointRef(checkpoint_id="cp-1",run_id="run-1",schema_version="1",step=0,state_hash="b"*64,created_at=now)
    fork=ForkRef(fork_run_id="run-2",parent_run_id="run-1",checkpoint_id=checkpoint.checkpoint_id,lineage_depth=1)
    assert fork.parent_run_id == checkpoint.run_id
    with pytest.raises(ValidationError): ForkRef(fork_run_id="run-2",parent_run_id="run-1",checkpoint_id="cp",lineage_depth=EXTENSION_POLICY.max_fork_depth+1)


def test_extension_event_redacts_and_caps_payload():
    event=ExtensionEvent(namespace="repl_sandbox",name="repl.failed",run_id="run-1",payload={"api_key":"secret","message":"bearer abc"})
    assert event.contract_version == "1"
    with pytest.raises(ValidationError):
        ExtensionEvent(namespace="repl_sandbox",name="repl.failed",run_id="run-1",phase="failed",payload={})
    assert event.payload["api_key"] == "[REDACTED]"
    assert "[REDACTED]" in event.payload["message"]
    bounded=ExtensionEvent(namespace="repl_sandbox",name="repl.output",run_id="run-1",payload={"data":"x"*(EXTENSION_POLICY.max_event_bytes+1)})
    assert len(json.dumps(bounded.payload).encode()) <= EXTENSION_POLICY.max_event_bytes


def test_extension_control_and_error_codes_are_bounded():
    from app.core.extension_contracts import ExtensionControl, ExtensionErrorCode
    assert ExtensionControl(command="cancel",request_id="r-1").contract_version == "1"
    assert ExtensionErrorCode.LIMIT_EXCEEDED.value == "extension.limit_exceeded"
    with pytest.raises(ValidationError): ExtensionControl(command="delete",request_id="r-1")


def test_capability_descriptor_is_strict_and_deterministic():
    descriptor=CapabilityDescriptor(provider="local",kind="llm",version="1",capabilities=["chat.complete"],metadata={})
    assert descriptor.capabilities == ["chat.complete"]
    safe=CapabilityDescriptor(provider="local",kind="llm",version="1",capabilities=[],metadata={"api_key":"secret"})
    assert safe.metadata["api_key"] == "[REDACTED]"
    with pytest.raises(ValidationError): CapabilityDescriptor(provider="local",kind="llm",version="1",capabilities=["bad capability"],metadata={})
