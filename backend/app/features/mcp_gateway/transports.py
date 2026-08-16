"""Bounded JSON-RPC transports for approved MCP manifests."""
from __future__ import annotations
import asyncio,json,os,shutil,signal,sys,uuid
from typing import Any
import httpx
from app.core.extension_contracts import EXTENSION_POLICY
from app.features.mcp_gateway.contracts import ServerManifest

class McpTransportError(RuntimeError): pass

class StdioTransport:
    async def request(self,manifest: ServerManifest,method: str,params: dict[str,Any])->dict[str,Any]:
        node_bin = shutil.which("node") or shutil.which("nodejs") or "/usr/bin/node"
        command=[sys.executable,manifest.command,*manifest.args] if (manifest.command or "").endswith(".py") else (["/bin/sh",manifest.command,*manifest.args] if (manifest.command or "").endswith(".sh") else [node_bin,manifest.command,*manifest.args])
        env={"PATH":"/usr/bin:/bin","PYTHONUNBUFFERED":"1","HARNESSFORGE_MCP_LOCAL_TRUST":"1"}
        process=await asyncio.create_subprocess_exec(*command,cwd=manifest.workspace_path,env=env,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,start_new_session=True,limit=EXTENSION_POLICY.max_mcp_response_bytes)
        async def drain():
            if process.stderr:
                while await process.stderr.read(8192): pass
        drain_task=asyncio.create_task(drain())
        request={"jsonrpc":"2.0","id":uuid.uuid4().hex,"method":method,"params":params}
        try:
            process.stdin.write((json.dumps(request,separators=(",",":"))+"\n").encode()); await process.stdin.drain()
            while True:
                line=await asyncio.wait_for(process.stdout.readline(),timeout=60)
                if not line or len(line)>EXTENSION_POLICY.max_mcp_response_bytes: raise McpTransportError("MCP stdio response exceeded limit")
                response=json.loads(line)
                if not isinstance(response,dict): raise McpTransportError("MCP response is invalid")
                if response.get("id")==request["id"]:
                    if "error" in response: raise McpTransportError("MCP request failed")
                    return response
        except asyncio.TimeoutError as exc: raise McpTransportError("MCP request timed out") from exc
        except (BrokenPipeError,ConnectionError,ValueError,TypeError) as exc: raise McpTransportError("MCP transport failed") from exc
        finally:
            if process.returncode is None:
                try: os.killpg(process.pid,signal.SIGTERM)
                except (ProcessLookupError,PermissionError): pass
                try: await asyncio.wait_for(process.wait(),timeout=1)
                except asyncio.TimeoutError:
                    try: os.killpg(process.pid,signal.SIGKILL)
                    except (ProcessLookupError,PermissionError): pass
                    await process.wait()
            drain_task.cancel(); await asyncio.gather(drain_task,return_exceptions=True)

class HttpTransport:
    async def request(self,manifest: ServerManifest,method: str,params: dict[str,Any])->dict[str,Any]:
        try:
            async with httpx.AsyncClient(follow_redirects=False,timeout=httpx.Timeout(60)) as client:
                response=await client.post(manifest.endpoint or "",json={"jsonrpc":"2.0","id":uuid.uuid4().hex,"method":method,"params":params})
                if response.status_code!=200 or len(response.content)>EXTENSION_POLICY.max_mcp_response_bytes: raise McpTransportError("MCP HTTP response invalid")
                if "text/event-stream" in response.headers.get("content-type",""):
                    data=[line[5:].strip() for line in response.text.splitlines() if line.startswith("data:")]
                    if not data: raise McpTransportError("MCP SSE response is empty")
                    payload=json.loads(data[-1])
                else: payload=response.json()
                if not isinstance(payload,dict) or "error" in payload: raise McpTransportError("MCP response is invalid")
                return payload
        except McpTransportError: raise
        except (httpx.HTTPError,ValueError,TypeError) as exc: raise McpTransportError("MCP HTTP transport failed") from exc

class SseTransport(HttpTransport): pass
