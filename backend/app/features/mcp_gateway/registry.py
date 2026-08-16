"""Explicit, file-backed MCP allowlist registry."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse
from ipaddress import ip_address
import socket
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.features.mcp_gateway.approval import approved_manifest,verify_manifest
from app.features.mcp_gateway.contracts import ServerManifest
from app.core.extension_contracts import EXTENSION_POLICY

class McpRegistryError(ValueError): pass

class McpRegistry:
    def __init__(self,workspace: str|Path,*,allowed_https_hosts: set[str]|None=None):
        try: self.boundary=WorkspaceBoundary(workspace)
        except UnsafePathError as exc: raise McpRegistryError("invalid MCP workspace") from exc
        self.allowed_https_hosts={host.casefold() for host in (allowed_https_hosts or set())}
        self.path=self.boundary.resolve(".harnessforge/mcp-registry.json")
        self._items:dict[str,ServerManifest]={}; self._load()

    def _load(self)->None:
        if not self.path.exists(): return
        try: data=json.loads(self.path.read_text(encoding="utf-8"));
        except (OSError,UnicodeError,ValueError) as exc: raise McpRegistryError("MCP registry is invalid") from exc
        if not isinstance(data,list) or len(data)>16: raise McpRegistryError("MCP registry is invalid")
        for item in data:
            manifest=ServerManifest.model_validate(item)
            self._validate(manifest)
            if manifest.approved and not verify_manifest(manifest): raise McpRegistryError("MCP approval fingerprint is invalid")
            self._items[manifest.server_id]=manifest

    def _validate_dns(self, host: str, port: int|None, *, loopback: bool) -> None:
        try: addresses=socket.getaddrinfo(host,port or 443,type=socket.SOCK_STREAM)
        except OSError as exc: raise McpRegistryError("MCP endpoint cannot be resolved") from exc
        if not addresses: raise McpRegistryError("MCP endpoint cannot be resolved")
        for address in addresses:
            try: resolved=ip_address(address[4][0])
            except (ValueError,IndexError): raise McpRegistryError("MCP endpoint resolution is invalid")
            if loopback and not resolved.is_loopback: raise McpRegistryError("MCP localhost resolution is unsafe")
            if not loopback and (resolved.is_private or resolved.is_loopback or resolved.is_link_local or resolved.is_reserved or resolved.is_multicast or resolved.is_unspecified): raise McpRegistryError("MCP endpoint resolves to a private address")

    def _validate_endpoint(self,endpoint: str)->None:
        parsed=urlparse(endpoint)
        try: port=parsed.port
        except ValueError as exc: raise McpRegistryError("invalid MCP endpoint") from exc
        if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname or parsed.path=="": raise McpRegistryError("invalid MCP endpoint")
        host=parsed.hostname.casefold(); loopback=False
        try: loopback=ip_address(host).is_loopback
        except ValueError: loopback=host=="localhost"
        if loopback:
            if parsed.scheme!="http": raise McpRegistryError("local MCP endpoint must use HTTP")
            if not ip_address(host).is_loopback if host not in {"localhost"} else False: raise McpRegistryError("invalid loopback endpoint")
            if host=="localhost": self._validate_dns(host,port,loopback=True)
        elif parsed.scheme!="https" or host not in self.allowed_https_hosts: raise McpRegistryError("MCP endpoint is not allowlisted")
        else: self._validate_dns(host,port,loopback=False)
        if port is not None and not 1<=port<=65535: raise McpRegistryError("invalid MCP endpoint port")

    def _validate(self,manifest: ServerManifest)->None:
        for value in [manifest.name,*manifest.args]:
            if any(token in value.casefold() for token in ("api_key","authorization","bearer ","secret=")): raise McpRegistryError("secret-shaped MCP manifest value")
        if manifest.transport=="stdio":
            try:
                if Path(manifest.workspace_path or "").resolve()!=self.boundary.workspace: raise McpRegistryError("MCP workspace mismatch")
                path=self.boundary.resolve(manifest.command or "",must_exist=True)
            except (UnsafePathError,OSError,RuntimeError) as exc: raise McpRegistryError("invalid MCP command path") from exc
            if path.suffix not in {".py",".sh",".js"}: raise McpRegistryError("unsupported MCP command")
            if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest.command_sha256: raise McpRegistryError("MCP command hash mismatch")
        else: self._validate_endpoint(manifest.endpoint or "")

    def register(self,manifest: ServerManifest)->ServerManifest:
        if len(self._items) >= EXTENSION_POLICY.max_mcp_servers: raise McpRegistryError("MCP server limit exceeded")
        self._validate(manifest)
        if manifest.server_id in self._items: raise McpRegistryError("MCP server already registered")
        review=manifest.model_copy(update={"approved":False,"approval_fingerprint":None})
        self._items[review.server_id]=review; self._save(); return review

    def approve(self,server_id: str)->ServerManifest:
        current=self.get(server_id); self._validate(current); approved=approved_manifest(current); self._items[server_id]=approved; self._save(); return approved

    def disable(self,server_id: str)->ServerManifest:
        current=self.get(server_id); disabled=current.model_copy(update={"approved":False,"approval_fingerprint":None}); self._items[server_id]=disabled; self._save(); return disabled

    def get(self,server_id: str)->ServerManifest:
        try: manifest=self._items[server_id]
        except KeyError as exc: raise McpRegistryError("MCP server is unknown") from exc
        self._validate(manifest)
        return manifest

    def list(self)->list[ServerManifest]: return list(self._items.values())

    def _save(self)->None:
        self.path.parent.mkdir(parents=True,exist_ok=True); content=json.dumps([item.model_dump(mode="json") for item in self._items.values()],ensure_ascii=False,indent=2).encode()
        fd,tmp=tempfile.mkstemp(prefix=".mcp-registry-",suffix=".tmp",dir=self.path.parent)
        try:
            with os.fdopen(fd,"wb") as handle: handle.write(content); handle.flush(); os.fsync(handle.fileno())
            os.replace(tmp,self.path)
        except OSError as exc:
            try: os.unlink(tmp)
            except OSError: pass
            raise McpRegistryError("MCP registry cannot be saved") from exc
