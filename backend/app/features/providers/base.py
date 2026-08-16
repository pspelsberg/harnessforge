"""Public provider adapter contract."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator, Protocol, Any
class CompletionRequest(Protocol):
    messages: list[dict[str,Any]]
class CompletionChunk(Protocol):
    text: str
class BaseProviderAdapter(ABC):
    @abstractmethod
    async def complete(self, request:CompletionRequest, **kwargs) -> AsyncIterator[CompletionChunk]: ...
