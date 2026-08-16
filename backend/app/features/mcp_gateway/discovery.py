"""Opt-in MCP discovery that produces review-only registry entries."""
from __future__ import annotations
from app.features.mcp_gateway.contracts import ServerManifest
from app.features.mcp_gateway.registry import McpRegistry,McpRegistryError

class McpDiscovery:
    def __init__(self,registry: McpRegistry): self.registry=registry
    def review_manifest(self,manifest: ServerManifest, *, enabled: bool=False)->ServerManifest:
        if not enabled: raise McpRegistryError("MCP discovery is disabled")
        # Registration deliberately forces approved=false; a human must approve later.
        return self.registry.register(manifest)
