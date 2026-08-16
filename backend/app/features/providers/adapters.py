"""Bounded, streaming outbound provider adapter."""
from __future__ import annotations
import os
import json
import hashlib
from dataclasses import dataclass
from typing import AsyncIterator, Any
from math import isfinite
import httpx
from app.core.config import CAPS
from app.features.providers.contracts import ProviderConfig, ProviderKind
from app.features.providers.base import BaseProviderAdapter

class ProviderError(RuntimeError): pass
@dataclass(frozen=True)
class ProviderRequest:
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
            if not isinstance(message, dict) or set(message) - {"role", "content", "source"} or not isinstance(message.get("role"), str) or message.get("role") not in {"system", "user", "assistant"} or not isinstance(message.get("content"), str):
                raise ValueError("messages must contain only supported roles and string content")
            if message.get("source", "trusted") not in {"trusted", "untrusted_context"}:
                raise ValueError("invalid message source")
            if message.get("source") == "untrusted_context" and message["role"] == "system":
                raise ValueError("untrusted context cannot be a system message")
@dataclass(frozen=True)
class CompletionChunk:
    text: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None

@dataclass(frozen=True)
class DataflowApproval:
    fingerprint: str
    @classmethod
    def issue(cls, config: ProviderConfig, bindings: list[str]) -> "DataflowApproval":
        return cls(_fingerprint(config, bindings))
    def valid_for(self, config: ProviderConfig, bindings: list[str]) -> bool:
        return self.fingerprint == _fingerprint(config, bindings)

def _fingerprint(config: ProviderConfig, bindings: list[str]) -> str:
    payload=json.dumps({"kind":config.kind.value,"base_url":config.base_url,"model":config.model,"bindings":sorted(bindings)},separators=(",",":"),sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

class OpenAICompatibleAdapter(BaseProviderAdapter):
    def __init__(self, config: ProviderConfig, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.config=config
        self._client=httpx.AsyncClient(transport=transport, follow_redirects=False, timeout=httpx.Timeout(config.timeout_seconds, connect=config.timeout_seconds))
    async def aclose(self) -> None: await self._client.aclose()
    async def complete(self, request: ProviderRequest, **kwargs) -> AsyncIterator[CompletionChunk]:
        async for chunk in self.stream(request, **kwargs): yield chunk
    async def stream(self, request: ProviderRequest, *, approval: DataflowApproval | None = None, bindings: list[str] | None = None, referer: str | None = None, title: str | None = None) -> AsyncIterator[CompletionChunk]:
        bindings=bindings or []
        if self.config.kind in {ProviderKind.OPENAI,ProviderKind.OPENROUTER} and (approval is None or not approval.valid_for(self.config, bindings)):
            raise ProviderError("external dataflow approval required")
        if len(json.dumps(request.messages, ensure_ascii=False).encode()) > CAPS.max_event_bytes:
            raise ProviderError("request too large")
        # Re-validate mutable/copy-derived configs immediately before network I/O.
        from app.features.providers.contracts import validate_provider_url
        validate_provider_url(self.config.base_url, self.config.kind)
        external = self.config.kind in {ProviderKind.OPENAI, ProviderKind.OPENROUTER}
        canonical_secret_env="OPENAI_API_KEY" if self.config.kind == ProviderKind.OPENAI else "OPENROUTER_API_KEY" if self.config.kind == ProviderKind.OPENROUTER else ""
        key=os.environ.get(canonical_secret_env) if external else None
        if external and not key:
            raise ProviderError("provider secret is unavailable")
        headers={"authorization":f"Bearer {key}"} if external and key else {}
        if self.config.kind == ProviderKind.OPENROUTER:
            referer = referer if referer is not None else self.config.referer
            title = title if title is not None else self.config.title
            if referer is not None and (not isinstance(referer,str) or len(referer)>512 or not referer.startswith("https://")): raise ProviderError("invalid OpenRouter referer")
            if title is not None and (not isinstance(title,str) or len(title)>128): raise ProviderError("invalid OpenRouter title")
            if referer: headers["HTTP-Referer"]=referer
            if title: headers["X-Title"]=title
        is_ollama=self.config.kind == ProviderKind.OLLAMA
        payload={"model":self.config.model,"messages":request.messages,"stream":False if is_ollama else True}
        endpoint=self.config.base_url.rstrip("/") + ("/api/chat" if is_ollama else "/chat/completions")
        if request.temperature is not None: payload["temperature"]=request.temperature
        if request.max_tokens is not None: payload["max_tokens"]=min(request.max_tokens, 8192)
        try:
            async with self._client.stream("POST", endpoint,headers=headers,json=payload) as response:
                if response.status_code != 200:
                    raise ProviderError(f"provider returned status {response.status_code}")
                length=response.headers.get("content-length")
                if length and (not length.isdigit() or int(length) > CAPS.max_event_bytes):
                    raise ProviderError("provider response exceeded limit")
                body=bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > CAPS.max_event_bytes:
                        raise ProviderError("provider response exceeded limit")
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError("provider request failed") from exc
        content_type=response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            for raw_line in bytes(body).splitlines():
                if not raw_line.startswith(b"data:"): continue
                raw=raw_line[5:].strip()
                if raw==b"[DONE]": continue
                try:
                    event=json.loads(raw); choices=event.get("choices",[])
                    if not choices: continue
                    choice=choices[0]; delta=choice.get("delta",{}); text=delta.get("content",""); finish_reason=choice.get("finish_reason")
                except (ValueError,KeyError,IndexError,TypeError) as exc: raise ProviderError("provider stream was invalid") from exc
                if text: yield CompletionChunk(text=text,finish_reason=finish_reason)
            return
        try:
            data=json.loads(bytes(body))
            if is_ollama:
                text=data["message"]["content"]; finish_reason=None
            else:
                choices=data["choices"]
                if not isinstance(choices,list) or not choices: raise ValueError
                item=choices[0]; content=item.get("message", item.get("delta", {})); text=content.get("content",""); finish_reason=item.get("finish_reason")
        except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError("provider response was invalid") from exc
        if not isinstance(text,str) or len(text.encode()) > CAPS.max_event_bytes:
            raise ProviderError("provider output exceeded limit")
        usage=data.get("usage", {}) if isinstance(data, dict) and isinstance(data.get("usage",{}),dict) else {}
        prompt_tokens=usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"),int) and 0<=usage.get("prompt_tokens")<=100000000 else None
        completion_tokens=usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"),int) and 0<=usage.get("completion_tokens")<=100000000 else None
        yield CompletionChunk(text=text,finish_reason=finish_reason,prompt_tokens=prompt_tokens,completion_tokens=completion_tokens,cost=data.get("cost") if isinstance(data.get("cost"),(int,float)) else None)
