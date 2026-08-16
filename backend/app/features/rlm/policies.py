"""RLM governance checks before any child task is created."""
from __future__ import annotations
from app.core.extension_contracts import EXTENSION_POLICY, CapabilityDescriptor
from app.features.rlm.contracts import ChildAgentSpec

class RlmPolicyError(ValueError): pass

def validate_spec(spec: ChildAgentSpec, *, allowed_bindings: set[str], capability: CapabilityDescriptor | None = None) -> None:
    if not set(spec.context.bindings).issubset(allowed_bindings): raise RlmPolicyError("unknown context binding")
    if spec.depth>EXTENSION_POLICY.max_rlm_depth: raise RlmPolicyError("RLM depth limit exceeded")
    if capability is not None and spec.provider != capability.provider: raise RlmPolicyError("provider capability mismatch")
    if capability is not None and "chat.complete" not in capability.capabilities: raise RlmPolicyError("provider lacks child-agent capability")
