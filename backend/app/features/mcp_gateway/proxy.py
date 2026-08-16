"""Governed MCP tool proxy with untrusted result projection."""
from __future__ import annotations
import asyncio
from typing import Any
from app.core.extension_contracts import EXTENSION_POLICY
from app.core.security.redaction import redact_payload
from app.features.mcp_gateway.contracts import McpCallRequest,McpCallResult
from app.features.mcp_gateway.registry import McpRegistry,McpRegistryError
from app.features.mcp_gateway.transports import HttpTransport,McpTransportError,SseTransport,StdioTransport
from app.features.mcp_gateway.contracts import ToolDescriptor
from app.features.mcp_gateway.schema_filter import McpSchemaError,validate_arguments
from app.features.mcp_gateway.approval import verify_manifest

class McpProxyError(RuntimeError): pass

class McpGateway:
    def __init__(self,registry: McpRegistry):
        self.registry=registry; self._counts:dict[tuple[str,str],int]={}; self._tools:dict[tuple[str,str],ToolDescriptor]={}

    def register_tools(self, tools: list[ToolDescriptor]) -> None:
        if len(tools)>64: raise McpProxyError("too many MCP tools")
        for tool in tools:
            if tool.server_id not in [manifest.server_id for manifest in self.registry.list()]: raise McpProxyError("unknown MCP server")
            self._tools[(tool.server_id,tool.name)]=tool

    async def call_tool(self,request: McpCallRequest)->McpCallResult:
        try: manifest=self.registry.get(request.server_id)
        except McpRegistryError as exc: return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="failed",error_code="mcp.unknown_server")
        if not verify_manifest(manifest) or request.approval_fingerprint != manifest.approval_fingerprint:
            return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="failed",error_code="mcp.approval_required")
        tool=self._tools.get((request.server_id,request.tool_name))
        if tool is None:
            return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="failed",error_code="mcp.tool_not_allowed")
        try: validate_arguments(tool,request.arguments)
        except McpSchemaError: return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="failed",error_code="mcp.invalid_arguments")
        key=(request.run_id,request.server_id)
        if key not in self._counts and len(self._counts) >= EXTENSION_POLICY.max_mcp_calls_per_run * 128:
            return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="limited",error_code="mcp.rate_limit")
        count=self._counts.get(key,0)
        if count>=EXTENSION_POLICY.max_mcp_calls_per_run: return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="limited",error_code="mcp.rate_limit")
        self._counts[key]=count+1
        transport=StdioTransport() if manifest.transport=="stdio" else SseTransport() if manifest.transport=="sse" else HttpTransport()
        try:
            response=await transport.request(manifest,"tools/call",{"name":request.tool_name,"arguments":request.arguments})
            content=redact_payload(response.get("result",response))
            return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="succeeded",content=content)
        except asyncio.CancelledError: raise
        except (McpTransportError,ValueError,TypeError): return McpCallResult(run_id=request.run_id,server_id=request.server_id,tool_name=request.tool_name,status="failed",error_code="mcp.transport_failed")
