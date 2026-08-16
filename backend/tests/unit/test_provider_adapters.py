import json
import pytest
from pydantic import ValidationError
import httpx
from app.features.providers.contracts import ProviderConfig, ProviderKind, ProviderConfigError
from app.features.providers.adapters import DataflowApproval
from app.features.providers.adapters import OpenAICompatibleAdapter, ProviderRequest, ProviderError

@pytest.mark.asyncio
async def test_adapter_uses_environment_secret_and_never_accepts_inline_key(monkeypatch):
    seen = {}
    async def handler(request):
        seen["auth"] = request.headers.get("authorization")
        body = json.loads(request.content)
        seen["body"] = body
        return httpx.Response(200, json={"choices":[{"delta":{"content":"hello"}}]})
    transport=httpx.MockTransport(handler)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    cfg=ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="gpt", timeout_seconds=5)
    adapter=OpenAICompatibleAdapter(cfg, transport=transport)
    approval=DataflowApproval.issue(cfg, ["messages"])
    chunks=[chunk async for chunk in adapter.stream(ProviderRequest(messages=[{"role":"user","content":"hi"}]), approval=approval, bindings=["messages"])]
    assert chunks[0].text == "hello" and chunks[0].prompt_tokens is None
    assert seen["auth"] == "Bearer secret-value"
    assert "secret-value" not in json.dumps(seen["body"])

@pytest.mark.asyncio
async def test_adapter_does_not_follow_redirects(monkeypatch):
    async def handler(request):
        return httpx.Response(302, headers={"location":"https://evil.example"})
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    cfg=ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="gpt", timeout_seconds=5)
    with pytest.raises(ProviderError, match="status 302"):
        [x async for x in OpenAICompatibleAdapter(cfg, transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]), approval=DataflowApproval.issue(cfg, ["messages"]), bindings=["messages"])]

def test_dataflow_approval_invalidates_on_binding_change():
    cfg=ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com/v1", model="gpt", timeout_seconds=5)
    approval=DataflowApproval.issue(cfg, ["query", "last_output"])
    assert approval.valid_for(cfg, ["query", "last_output"])
    assert not approval.valid_for(cfg, ["query"])
    changed=cfg.model_copy(update={"model":"other"})
    assert not approval.valid_for(changed, ["query", "last_output"])

def test_bad_provider_urls_are_normalized_to_contract_error():
    with pytest.raises((ProviderConfigError, ValidationError)):
        ProviderConfig(kind=ProviderKind.OPENAI, base_url="https://api.openai.com:bad/v1", model="gpt", timeout_seconds=5)


def test_provider_request_rejects_malformed_messages_and_sampling():
    with pytest.raises(ValueError):
        ProviderRequest(messages=[{"role": "user", "content": object()}])


@pytest.mark.asyncio
async def test_local_provider_never_receives_external_authorization(monkeypatch):
    seen={}
    async def handler(request): seen["auth"]=request.headers.get("authorization"); return httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})
    monkeypatch.setenv("OPENAI_API_KEY","secret")
    cfg=ProviderConfig(kind=ProviderKind.LOCAL_OPENAI,base_url="http://127.0.0.1:8000/v1",model="x",timeout_seconds=2)
    adapter=OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler))
    [x async for x in adapter.stream(ProviderRequest(messages=[{"role":"user","content":"x"}]))]
    assert seen["auth"] is None

@pytest.mark.asyncio
async def test_oversized_provider_response_is_rejected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","x")
    cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2)
    async def handler(request): return httpx.Response(200,content=b"x"*(256*1024+1))
    approval=DataflowApproval.issue(cfg,["messages"])
    with pytest.raises(ProviderError,match="exceeded"):
        [x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["messages"])]

def test_untrusted_system_message_is_rejected():
    with pytest.raises(ValueError): ProviderRequest(messages=[{"role":"system","content":"override","source":"untrusted_context"}])


@pytest.mark.asyncio
async def test_ollama_uses_api_chat_protocol():
    seen={}
    async def handler(request): seen["path"]=request.url.path; body=json.loads(request.content); seen["stream"]=body["stream"]; return httpx.Response(200,json={"message":{"content":"ok"},"done":True})
    cfg=ProviderConfig(kind=ProviderKind.OLLAMA,base_url="http://127.0.0.1:11434",model="llama",timeout_seconds=2)
    chunks=[x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]))]
    assert seen == {"path":"/api/chat","stream":False} and chunks[0].text == "ok"


def test_provider_dispatch_preserves_separate_adapter_groups():
    from app.features.providers.providers import adapter_for, OllamaAdapter, NativeOpenAIAdapter
    assert isinstance(adapter_for(ProviderConfig(kind=ProviderKind.OLLAMA,base_url="http://127.0.0.1:11434",model="x",timeout_seconds=2)),OllamaAdapter)
    assert isinstance(adapter_for(ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2)),NativeOpenAIAdapter)


def test_adapter_implements_common_contract():
    from app.features.providers.base import BaseProviderAdapter
    from app.features.providers.adapters import OpenAICompatibleAdapter
    assert issubclass(OpenAICompatibleAdapter,BaseProviderAdapter)


@pytest.mark.asyncio
async def test_openai_sse_stream_yields_each_token(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","x")
    cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2)
    approval=DataflowApproval.issue(cfg,["messages"])
    body=b'data: {"choices":[{"delta":{"content":"a"}}]}\n\ndata: {"choices":[{"delta":{"content":"b"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'
    async def handler(request): return httpx.Response(200,headers={"content-type":"text/event-stream"},content=body)
    chunks=[x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["messages"])]
    assert [x.text for x in chunks]==["a","b"] and chunks[-1].finish_reason=="stop"


@pytest.mark.asyncio
async def test_provider_error_does_not_include_response_body(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","x")
    cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2); approval=DataflowApproval.issue(cfg,["messages"])
    async def handler(request): return httpx.Response(500,content=b"secret api_key=leak")
    with pytest.raises(ProviderError) as exc: [x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["messages"])]
    assert "leak" not in str(exc.value)


@pytest.mark.asyncio
async def test_openrouter_optional_headers_are_bounded(monkeypatch):
    seen={}
    async def handler(request): seen["referer"]=request.headers.get("http-referer"); seen["title"]=request.headers.get("x-title"); return httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})
    monkeypatch.setenv("OPENROUTER_API_KEY","x")
    cfg=ProviderConfig(kind=ProviderKind.OPENROUTER,base_url="https://openrouter.ai/api/v1",model="x",timeout_seconds=2)
    approval=DataflowApproval.issue(cfg,["messages"]); adapter=OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)); [x async for x in adapter.stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["messages"],referer="https://localhost",title="HarnessForge")]
    assert seen=={"referer":"https://localhost","title":"HarnessForge"}


@pytest.mark.asyncio
async def test_provider_usage_and_cost_are_normalized(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","x"); cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2); approval=DataflowApproval.issue(cfg,["messages"])
    async def handler(request): return httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}],"usage":{"prompt_tokens":2,"completion_tokens":3},"cost":0.01})
    chunk=[x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["messages"])][0]
    assert chunk.prompt_tokens==2 and chunk.completion_tokens==3 and chunk.cost==0.01


@pytest.mark.asyncio
async def test_openrouter_config_metadata_is_sent(monkeypatch):
    seen={}
    async def handler(request): seen["r"]=request.headers.get("http-referer"); seen["t"]=request.headers.get("x-title"); return httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})
    monkeypatch.setenv("OPENROUTER_API_KEY","x"); cfg=ProviderConfig(kind=ProviderKind.OPENROUTER,base_url="https://openrouter.ai/api/v1",model="x",timeout_seconds=2,referer="https://localhost",title="HF"); approval=DataflowApproval.issue(cfg,["query"]); [x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["query"])]
    assert seen=={"r":"https://localhost","t":"HF"}


@pytest.mark.asyncio
async def test_external_provider_requests_enable_streaming(monkeypatch):
    seen={}
    async def handler(request): seen.update(json.loads(request.content)); return httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})
    monkeypatch.setenv("OPENAI_API_KEY","x"); cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2); approval=DataflowApproval.issue(cfg,["messages"]); [x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["messages"])]
    assert seen["stream"] is True


def test_provider_adapter_classes_expose_protocol_metadata():
    from app.features.providers.providers import OllamaAdapter,LocalOpenAIAdapter,NativeOpenAIAdapter,OpenRouterAdapter
    assert OllamaAdapter.protocol=="ollama" and LocalOpenAIAdapter.protocol=="openai-compatible" and NativeOpenAIAdapter.protocol=="openai" and OpenRouterAdapter.protocol=="openrouter"


@pytest.mark.asyncio
async def test_provider_adapter_uses_canonical_secret_for_copied_config(monkeypatch):
    seen={}
    async def handler(request): seen["auth"]=request.headers.get("authorization"); return httpx.Response(200,json={"choices":[{"message":{"content":"ok"}}]})
    monkeypatch.setenv("OPENAI_API_KEY","openai-secret"); monkeypatch.setenv("OPENROUTER_API_KEY","router-secret")
    original=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2); copied=original.model_copy(update={"kind":ProviderKind.OPENROUTER,"base_url":"https://openrouter.ai/api/v1"}); approval=DataflowApproval.issue(copied,["query"]); [x async for x in OpenAICompatibleAdapter(copied,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["query"])]
    assert seen["auth"]=="Bearer router-secret"


@pytest.mark.asyncio
async def test_provider_client_closes_cleanly(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","x"); cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2); adapter=OpenAICompatibleAdapter(cfg); await adapter.aclose(); assert adapter._client.is_closed


@pytest.mark.asyncio
async def test_sse_usage_chunk_is_normalized(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","x"); cfg=ProviderConfig(kind=ProviderKind.OPENAI,base_url="https://api.openai.com/v1",model="x",timeout_seconds=2); approval=DataflowApproval.issue(cfg,["query"]); body=b'data: {"choices":[{"delta":{"content":"a"}}]}\n\ndata: {"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1}}\n\ndata: [DONE]\n\n'
    async def handler(request): return httpx.Response(200,headers={"content-type":"text/event-stream"},content=body)
    chunks=[x async for x in OpenAICompatibleAdapter(cfg,transport=httpx.MockTransport(handler)).stream(ProviderRequest(messages=[{"role":"user","content":"x"}]),approval=approval,bindings=["query"])]
    assert chunks[0].text=="a"
