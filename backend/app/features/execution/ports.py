"""Public ports for execution integrations; implementations stay in their slices."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, AsyncIterator
class ProviderPort(Protocol):
    async def complete(self, request: Any, **kwargs) -> AsyncIterator[Any]: ...
class RetrievalPort(Protocol):
    def search(self, path: str, table: str, vector: list[float], *, top_k: int = 5) -> list[dict[str, Any]]: ...
class ToolPort(Protocol):
    async def run(self, spec: Any, *, approved_hash: str): ...
@dataclass(frozen=True)
class ExecutionServices:
    provider: ProviderPort | None = None
    retrieval: RetrievalPort | None = None
    tool: ToolPort | None = None
    providers: dict[str, ProviderPort] | None = None
    retrievals: dict[str, RetrievalPort] | None = None
    tools: dict[str, ToolPort] | None = None
    approvals: dict[str, Any] | None = None
    bindings: dict[str, list[str]] | None = None
    provider_approval: Any = None
    provider_bindings: list[str] | None = None
    prompt_loader: Any = None
