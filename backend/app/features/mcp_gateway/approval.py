"""MCP manifest approval fingerprinting."""
from __future__ import annotations
import hashlib,json
from app.features.mcp_gateway.contracts import ServerManifest

def manifest_fingerprint(manifest: ServerManifest)->str:
    data=manifest.model_dump(mode="json",exclude={"approved","approval_fingerprint"})
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def approved_manifest(manifest: ServerManifest)->ServerManifest:
    fingerprint=manifest_fingerprint(manifest)
    return manifest.model_copy(update={"approved":True,"approval_fingerprint":fingerprint})

def verify_manifest(manifest: ServerManifest)->bool:
    return manifest.approved and manifest.approval_fingerprint==manifest_fingerprint(manifest)
