"""Bounded, streaming outbound provider adapter."""
from __future__ import annotations
import os
import json
import hashlib
from dataclasses import dataclass
from typing import AsyncIterator, Any
import httpx
from app.core.config import CAPS
from app.features.providers.contracts import ProviderConfig, ProviderKind
from app.features.providers.base import BaseProviderAdapter, CompletionRequest, CompletionChunk

# Backwards-compatible feature-slice name; the public contract lives in base.py.
ProviderRequest = CompletionRequest

class ProviderError(RuntimeError): pass
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
        from app.features.providers.contracts import validate_provider_url
        validate_provider_url(self.config.base_url, self.config.kind)
        external = self.config.kind in {ProviderKind.OPENAI,ProviderKind.OPENROUTER}
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
                content_type=response.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    received=0
                    async for raw_line in response.aiter_lines():
                        received += len(raw_line.encode("utf-8"))+1
                        if received > CAPS.max_event_bytes:
                            raise ProviderError("provider response exceeded limit")
                        if not raw_line.startswith("data:"):
                            continue
                        raw=raw_line[5:].strip()
                        if raw=="[DONE]":
                            continue
                        try:
                            event=json.loads(raw); choices=event.get("choices",[])
                            if not choices: continue
                            choice=choices[0]; delta=choice.get("delta",{}); text=delta.get("content",""); finish_reason=choice.get("finish_reason")
                            chunk=CompletionChunk(text=text,finish_reason=finish_reason)
                        except (ValueError,KeyError,IndexError,TypeError,json.JSONDecodeError) as exc:
                            raise ProviderError("provider stream was invalid") from exc
                        if chunk.text or chunk.finish_reason:
                            yield chunk
                    return
                body=bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > CAPS.max_event_bytes:
                        raise ProviderError("provider response exceeded limit")
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
                try:
                    yield CompletionChunk(text=text,finish_reason=finish_reason,prompt_tokens=prompt_tokens,completion_tokens=completion_tokens,cost=data.get("cost") if isinstance(data.get("cost"),(int,float)) else None)
                except ValueError as exc:
                    raise ProviderError("provider usage was invalid") from exc
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError("provider request failed") from exc
