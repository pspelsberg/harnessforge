import asyncio, hashlib, json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.features.mcp_gateway.approval import manifest_fingerprint
from app.features.mcp_gateway.contracts import McpCallRequest,ServerManifest,ToolDescriptor
from app.features.mcp_gateway.proxy import McpGateway
from app.features.mcp_gateway.registry import McpRegistry,McpRegistryError
from app.features.mcp_gateway.schema_filter import filter_tool

def make_manifest(tmp_path):
    server=tmp_path/"server.py"
    server.write_text("import json,sys,os\nfor line in sys.stdin:\n r=json.loads(line); print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':{'content':{'text':'Bearer secret'},'env':bool(os.environ.get('OPENAI_API_KEY'))}},separators=(',',':')),flush=True)\n")
    return ServerManifest(server_id="srv-1",name="local",transport="stdio",command="server.py",workspace_path=str(tmp_path),command_sha256=hashlib.sha256(server.read_bytes()).hexdigest(),capabilities=["tools.call"])

@pytest.mark.asyncio
async def test_registry_requires_review_approval_tool_catalog_and_redacts_response(tmp_path):
    registry=McpRegistry(tmp_path); review=registry.register(make_manifest(tmp_path)); assert not review.approved
    gateway=McpGateway(registry); tool=ToolDescriptor(server_id="srv-1",name="echo",description="safe",input_schema={"type":"object","properties":{"text":{"type":"string"}},"required":["text"],"additionalProperties":False}); gateway.register_tools([tool])
    denied=await gateway.call_tool(McpCallRequest(run_id="run-1",server_id="srv-1",tool_name="echo",arguments={"text":"x"}))
    assert denied.error_code=="mcp.approval_required"
    approved=registry.approve("srv-1")
    result=await gateway.call_tool(McpCallRequest(run_id="run-1",server_id="srv-1",tool_name="echo",arguments={"text":"x"},approval_fingerprint=approved.approval_fingerprint))
    assert result.status=="succeeded" and result.source=="untrusted" and result.content["content"]["text"]=="Bearer [REDACTED]" and result.content["env"] is False

@pytest.mark.asyncio
async def test_proxy_rejects_unknown_or_invalid_tool_arguments(tmp_path):
    registry=McpRegistry(tmp_path); manifest=registry.approve("srv-1") if False else registry.register(make_manifest(tmp_path)); manifest=registry.approve("srv-1")
    gateway=McpGateway(registry); gateway.register_tools([ToolDescriptor(server_id="srv-1",name="echo",input_schema={"type":"object","properties":{"text":{"type":"string"}},"required":["text"],"additionalProperties":False})])
    bad=await gateway.call_tool(McpCallRequest(run_id="run-1",server_id="srv-1",tool_name="echo",arguments={},approval_fingerprint=manifest.approval_fingerprint)); assert bad.error_code=="mcp.invalid_arguments"
    unknown=await gateway.call_tool(McpCallRequest(run_id="run-1",server_id="srv-1",tool_name="missing",arguments={},approval_fingerprint=manifest.approval_fingerprint)); assert unknown.error_code=="mcp.tool_not_allowed"

def test_registry_rejects_ssrf_and_command_escape(tmp_path):
    registry=McpRegistry(tmp_path)
    with pytest.raises(McpRegistryError): registry.register(ServerManifest(server_id="evil",name="evil",transport="http",endpoint="http://169.254.169.254/latest"))
    with pytest.raises(McpRegistryError): registry.register(ServerManifest(server_id="evil",name="evil",transport="http",endpoint="https://evil.example/mcp"))
    with pytest.raises(ValidationError): ToolDescriptor(server_id="x",name="x",input_schema={"x":"y"*200000})

def test_progressive_schema_filter_hides_secret_description():
    tool=ToolDescriptor(server_id="srv",name="tool",description="Bearer secret",input_schema={"type":"object","properties":{"password":{"type":"string"},"x":{"type":"string"}}})
    view=filter_tool(tool); assert "Bearer [REDACTED]" in view["description"] and set(view["input_schema"]["properties"])=={"x"}

@pytest.mark.asyncio
async def test_approved_stdio_hash_is_rechecked_before_each_call(tmp_path):
    registry=McpRegistry(tmp_path); review=registry.register(make_manifest(tmp_path)); approved=registry.approve("srv-1")
    gateway=McpGateway(registry); gateway.register_tools([ToolDescriptor(server_id="srv-1",name="echo",input_schema={})])
    (tmp_path/"server.py").write_text("print('changed')")
    result=await gateway.call_tool(McpCallRequest(run_id="run-1",server_id="srv-1",tool_name="echo",approval_fingerprint=approved.approval_fingerprint))
    assert result.error_code=="mcp.unknown_server"


@pytest.mark.asyncio
async def test_mcp_human_gate_required_tool_fails_closed(tmp_path):
    registry=McpRegistry(tmp_path); review=registry.register(make_manifest(tmp_path)); approved=registry.approve("srv-1"); gateway=McpGateway(registry); gateway.register_tools([ToolDescriptor(server_id="srv-1",name="echo",requires_human_gate=True,input_schema={})]); result=await gateway.call_tool(McpCallRequest(run_id="run-1",server_id="srv-1",tool_name="echo",approval_fingerprint=approved.approval_fingerprint)); assert result.error_code=="mcp.approval_required"
