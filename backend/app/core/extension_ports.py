"""Public capability ports for Phase-2 slices.

Only protocols live here; implementations remain in feature slices.
"""
from __future__ import annotations

from typing import Any, Protocol, Sequence

from app.core.extension_contracts import (
    ApprovalDecision, ApprovalRequest, CapabilityDescriptor, CheckpointRef,
    ContextEnvelope, ForkRef,
)


class ExtensionBudgetPort(Protocol):
    async def reserve(self, *, run_id: str, dimension: str, amount: int) -> str: ...
    async def release(self, reservation_id: str) -> None: ...


class ContextFirewallPort(Protocol):
    async def wrap(self, envelope: ContextEnvelope) -> ContextEnvelope: ...
    async def aggregate(self, results: Sequence[ContextEnvelope]) -> ContextEnvelope: ...


class ApprovalPort(Protocol):
    async def create_request(self, request: ApprovalRequest) -> ApprovalRequest: ...
    async def decide(self, decision: ApprovalDecision) -> ApprovalDecision: ...


class CheckpointPort(Protocol):
    async def read(self, reference: CheckpointRef) -> dict[str, Any]: ...
    async def fork(self, reference: CheckpointRef, *, state: dict[str, Any]) -> ForkRef: ...


class CapabilityPort(Protocol):
    async def describe(self, provider: str) -> CapabilityDescriptor: ...


class ApprovalPortError(RuntimeError):
    """Stable cross-slice failure for an approval consume operation."""


class HumanApprovalPort(Protocol):
    async def consume(self, request: Any) -> Any: ...
