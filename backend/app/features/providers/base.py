"""Public provider request, response, and adapter contracts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite
from typing import Any, AsyncIterator

from app.core.config import CAPS


@dataclass(frozen=True)
class CompletionRequest:
    messages: list[dict[str, Any]]
    temperature: float | None = None
    max_tokens: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.messages, list) or not self.messages:
            raise ValueError("messages must be a non-empty list")
        if self.temperature is not None and (not isinstance(self.temperature, (int, float)) or isinstance(self.temperature, bool) or not 0 <= self.temperature <= 2):
            raise ValueError("temperature must be between 0 and 2")
        if self.max_tokens is not None and (not isinstance(self.max_tokens, int) or isinstance(self.max_tokens, bool) or not 1 <= self.max_tokens <= 8192):
            raise ValueError("max_tokens must be between 1 and 8192")
        for message in self.messages:
            if (not isinstance(message, dict) or set(message) - {"role", "content", "source"}
                    or message.get("role") not in {"system", "user", "assistant"}
                    or not isinstance(message.get("content"), str)):
                raise ValueError("messages must contain only supported roles and string content")
            source = message.get("source", "trusted")
            if source not in {"trusted", "untrusted_context"}:
                raise ValueError("invalid message source")
            if source == "untrusted_context" and message["role"] == "system":
                raise ValueError("untrusted context cannot be a system message")


@dataclass(frozen=True)
class CompletionChunk:
    text: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or len(self.text.encode("utf-8")) > CAPS.max_event_bytes:
            raise ValueError("completion text is too large")
        for name in ("prompt_tokens", "completion_tokens"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValueError("token counts must be non-negative integers")
        if self.cost is not None and (not isinstance(self.cost, (int, float)) or isinstance(self.cost, bool) or not isfinite(self.cost) or self.cost < 0):
            raise ValueError("cost must be a finite non-negative number")


class BaseProviderAdapter(ABC):
    @abstractmethod
    async def complete(self, request: CompletionRequest, **kwargs: Any) -> AsyncIterator[CompletionChunk]:
        """Yield normalized completion chunks for one bounded request."""
        raise NotImplementedError
