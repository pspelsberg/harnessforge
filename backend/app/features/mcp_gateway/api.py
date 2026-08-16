"""Authenticated MCP catalog, approval and proxy endpoints."""
from __future__ import annotations
from fastapi import APIRouter,HTTPException
from pydantic import ConfigDict,Field
from app.core.extension_contracts import ExtensionContract
from app.features.mcp_gateway.contracts import McpCallRequest,ServerManifest,ToolDescriptor
from app.features.mcp_gateway.discovery import McpDiscovery
from app.features.mcp_gateway.proxy import McpGateway,McpProxyError
from app.features.mcp_gateway.registry import McpRegistry,McpRegistryError

class DiscoverRequest(ExtensionContract):
    model_config=ConfigDict(strict=True,extra="forbid")
    enabled: bool=False
    manifest: ServerManifest

def router_for(registry: McpRegistry,gateway: McpGateway)->APIRouter:
    router=APIRouter(); discovery=McpDiscovery(registry)
    @router.get("/api/mcp/servers")
    async def servers(): return {"servers":[item.model_dump(mode="json") for item in registry.list()]}
    @router.post("/api/mcp/discover",status_code=201)
    async def discover(request: DiscoverRequest):
        try: return (discovery.review_manifest(request.manifest,enabled=request.enabled)).model_dump(mode="json")
        except McpRegistryError as exc: raise HTTPException(status_code=400,detail="MCP discovery rejected") from exc
    @router.post("/api/mcp/servers/{server_id}/approve")
    async def approve(server_id: str):
        try: return registry.approve(server_id).model_dump(mode="json")
        except McpRegistryError as exc: raise HTTPException(status_code=400,detail="MCP approval failed") from exc
    @router.post("/api/mcp/servers/{server_id}/disable")
    async def disable(server_id: str):
        try: return registry.disable(server_id).model_dump(mode="json")
        except McpRegistryError as exc: raise HTTPException(status_code=400,detail="MCP disable failed") from exc
    @router.post("/api/mcp/servers/{server_id}/tools")
    async def catalog(server_id: str, tools: list[ToolDescriptor]):
        try:
            if any(tool.server_id!=server_id for tool in tools): raise ValueError
            gateway.register_tools(tools); return {"accepted":len(tools)}
        except (McpProxyError,ValueError) as exc: raise HTTPException(status_code=400,detail="MCP catalog rejected") from exc
    @router.post("/api/mcp/tools/call")
    async def call(request: McpCallRequest): return (await gateway.call_tool(request)).model_dump(mode="json")
    return router
