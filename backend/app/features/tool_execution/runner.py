"""Workspace-bounded Local Trust Mode subprocess runner."""
from __future__ import annotations
import asyncio, hashlib, json, os, signal, sys
from dataclasses import dataclass, field
from pathlib import Path
from app.core.config import CAPS
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
from app.core.extension_ports import HumanApprovalPort, ApprovalPortError
from typing import Any
class ToolError(RuntimeError): pass
@dataclass(frozen=True)
class ToolSpec:
    path: str
    args: list[str]
    timeout_seconds: float = 15.0
    allowed_write_dirs: list[str] = field(default_factory=list)
    env_allowlist: list[str] = field(default_factory=list)
    requires_human_gate: bool = False
    def __post_init__(self):
        if not self.path or len(self.path)>4096 or any(not isinstance(x,str) or len(x)>1024 for x in self.args): raise ValueError("invalid tool spec")
        if not 0 < self.timeout_seconds <= CAPS.max_tool_timeout_seconds: raise ValueError("invalid tool timeout")
        blocked={"OPENAI_API_KEY","OPENROUTER_API_KEY","HARNESSFORGE_SESSION_TOKEN","AWS_SECRET_ACCESS_KEY"}
        if len(self.env_allowlist)>64 or any(not isinstance(name, str) or len(name)>128 or not name.isidentifier() or name in blocked for name in self.env_allowlist): raise ValueError("invalid environment name")
@dataclass(frozen=True)
class ToolResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    trust_mode: str = "local_trust_mode"
class ToolRunner:
    def __init__(self, workspace: str|Path): self.boundary=WorkspaceBoundary(workspace)
    def _path(self,spec: ToolSpec) -> Path:
        try: path=self.boundary.resolve(spec.path,must_exist=True)
        except UnsafePathError as exc: raise ToolError("tool path is outside workspace") from exc
        if path.suffix not in {".py",".sh",".js"}: raise ToolError("unsupported tool type")
        if not path.is_file(): raise ToolError("tool is not a file")
        return path
    def config_hash(self,spec: ToolSpec) -> str:
        path=self._path(spec)
        write_paths=[]
        for candidate in spec.allowed_write_dirs:
            if not candidate: raise ToolError("invalid write directory")
            try: resolved=self.boundary.resolve(candidate, must_exist=True)
            except UnsafePathError as exc: raise ToolError("write directory is outside workspace") from exc
            if not resolved.is_dir(): raise ToolError("write directory is not a directory")
            write_paths.append(str(resolved.relative_to(self.boundary.workspace)))
        stat=path.stat()
        payload={"path":str(path.relative_to(self.boundary.workspace)),"content":hashlib.sha256(path.read_bytes()).hexdigest(),"mtime_ns":stat.st_mtime_ns,"args":spec.args,"env":sorted(spec.env_allowlist),"writes":sorted(write_paths),"timeout":spec.timeout_seconds,"requires_human_gate":spec.requires_human_gate}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def validate_write_target(self, relative_target: str, allowed_write_dirs: list[str]) -> Path:
        try: target=self.boundary.resolve(relative_target,must_exist=False)
        except UnsafePathError as exc: raise ToolError("write target is outside workspace") from exc
        for directory in allowed_write_dirs:
            try: root=self.boundary.resolve(directory,must_exist=True)
            except UnsafePathError: continue
            if root==target or self.boundary._inside(target,root): return target
        raise ToolError("write target is not declared")
    async def run(self,spec: ToolSpec, *, approved_hash: str, approval_request: Any | None = None, approval_port: HumanApprovalPort | None = None) -> ToolResult:
        path=self._path(spec)
        expected_hash=self.config_hash(spec)
        if approved_hash != expected_hash: raise ToolError("tool approval hash mismatch")
        if spec.requires_human_gate:
            if approval_request is None or approval_port is None: raise ToolError("human gate required for tool action")
            try: gate=await approval_port.consume(approval_request)
            except ApprovalPortError as exc: raise ToolError("human gate rejected tool action") from exc
            if getattr(gate,"gate_class",None)!="tool_write" or getattr(gate,"preview",None) is None or gate.preview.action!="tool.execute" or gate.preview.command!=f"tool:{spec.path}:{expected_hash}": raise ToolError("human gate binding mismatch")
        env={"PATH":"/usr/bin:/bin","PYTHONUNBUFFERED":"1","HARNESSFORGE_LOCAL_TRUST_MODE":"1","HARNESSFORGE_ALLOWED_WRITE_DIRS":os.pathsep.join(spec.allowed_write_dirs)}
        for name in spec.env_allowlist:
            if name in os.environ and name not in {"OPENAI_API_KEY","OPENROUTER_API_KEY","HARNESSFORGE_SESSION_TOKEN"}: env[name]=os.environ[name]
        if path.suffix==".py": command=[sys.executable,str(path),*spec.args]
        elif path.suffix==".sh": command=["/bin/sh",str(path),*spec.args]
        else:
            if not Path("/usr/bin/node").is_file():
                raise ToolError("node runtime is unavailable")
            command=["/usr/bin/node",str(path),*spec.args]
        process=await asyncio.create_subprocess_exec(*command,cwd=self.boundary.workspace,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,start_new_session=True)
        async def read_capped(stream: asyncio.StreamReader) -> bytes:
            data = bytearray()
            while True:
                chunk = await stream.read(min(8192, CAPS.max_output_bytes + 1 - len(data)))
                if not chunk: return bytes(data)
                data.extend(chunk)
                if len(data) > CAPS.max_output_bytes:
                    raise ToolError("tool output exceeded limit")
        try:
            stdout, stderr = await asyncio.wait_for(asyncio.gather(read_capped(process.stdout), read_capped(process.stderr)), timeout=spec.timeout_seconds)
        except ToolError:
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            await asyncio.sleep(0)
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    while await stream.read(8192): pass
            await process.wait()
            raise
        except asyncio.TimeoutError:
            try: os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: await asyncio.wait_for(process.communicate(),timeout=1)
            except asyncio.TimeoutError:
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                await process.communicate()
            return ToolResult(-signal.SIGTERM,"","tool timed out",True)
        return ToolResult(process.returncode or 0,stdout[:CAPS.max_output_bytes].decode("utf-8","replace"),stderr[:CAPS.max_output_bytes].decode("utf-8","replace"))
