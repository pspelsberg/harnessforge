"""Persistent, bounded subprocess REPL runner."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import sys
import textwrap
import uuid
from typing import Any
import time

from app.core.extension_contracts import EXTENSION_POLICY
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
from app.features.repl_sandbox.contracts import ReplExecuteRequest, ReplResult, ReplSessionInfo, ReplStatus
from app.features.repl_sandbox.policy import ReplPolicyError, validate_code
from app.features.repl_sandbox.redaction import redact_repl_result

class ReplError(RuntimeError): pass
class ReplLimitError(ReplError): pass

_WORKER = textwrap.dedent(r"""
    import builtins, contextlib, io, json, math, sys

    class OutputLimit(Exception): pass
    class CappedWriter(io.TextIOBase):
        def __init__(self, cap): self.cap=cap; self.data=[]; self.size=0
        def write(self, value):
            encoded=value.encode("utf-8")
            if self.size + len(encoded) > self.cap: raise OutputLimit()
            self.data.append(value); self.size += len(encoded); return len(value)
        def flush(self): return None
        def getvalue(self): return "".join(self.data)

    def safe_json(value, cap):
        try: encoded=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":"))
        except (TypeError,ValueError): raise ValueError("result is not JSON")
        if len(encoded.encode("utf-8")) > cap: raise OutputLimit()
        return value

    safe_builtins={name: getattr(builtins,name) for name in (
        "abs","all","any","bool","dict","enumerate","float","int","len",
        "list","max","min","print","range","round","set","sorted","str",
        "sum","tuple","zip") if hasattr(builtins,name)}
    namespace={"__builtins__":safe_builtins,"math":math,"json":json,"input_data":{}}
    cap=int(sys.argv[1])
    for raw in sys.stdin:
        try:
            request=json.loads(raw)
            namespace["input_data"]=request.get("input_data",{})
            output=CappedWriter(cap)
            with contextlib.redirect_stdout(output):
                exec(request["code"],namespace,namespace)
            result=safe_json(namespace.get("result"),cap)
            response={"status":"succeeded","stdout":output.getvalue(),"result":result}
        except OutputLimit:
            response={"status":"limited","stdout":"","result":None,"error_code":"repl.output_limit"}
        except Exception:
            response={"status":"failed","stdout":"","result":None,"error_code":"repl.execution_failed"}
        try:
            encoded=json.dumps(response,ensure_ascii=False,allow_nan=False,separators=(",",":"))
            if len(encoded.encode("utf-8")) > cap * 2:
                response={"status":"limited","stdout":"","result":None,"error_code":"repl.response_limit"}
                encoded=json.dumps(response,separators=(",",":"))
        except Exception:
            encoded=json.dumps({"status":"failed","stdout":"","result":None,"error_code":"repl.response_invalid"},separators=(",",":"))
        sys.__stdout__.write(encoded+"\n"); sys.__stdout__.flush()
""")

@dataclass
class _Process:
    process: asyncio.subprocess.Process
    stderr_task: asyncio.Task[Any]
    cells: int = 0
    created_at: float = 0.0
    last_activity: float = 0.0

class ReplRunner:
    def __init__(self, workspace: str | Path):
        try: self.boundary=WorkspaceBoundary(workspace)
        except UnsafePathError as exc: raise ReplError("invalid REPL workspace") from exc

    @staticmethod
    def _limits() -> None:
        try:
            import resource
            cpu=max(1,int(EXTENSION_POLICY.max_repl_seconds))
            memory=EXTENSION_POLICY.max_repl_memory_bytes
            resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu+1))
            resource.setrlimit(resource.RLIMIT_AS,(memory,memory))
        except (ImportError,OSError,ValueError):
            return None

    async def start(self) -> _Process:
        env={"PATH":"/usr/bin:/bin","PYTHONNOUSERSITE":"1","PYTHONUNBUFFERED":"1","HARNESSFORGE_LOCAL_TRUST_MODE":"1"}
        process=await asyncio.create_subprocess_exec(
            sys.executable,"-I","-S","-u","-c",_WORKER,str(EXTENSION_POLICY.max_repl_output_bytes),
            cwd=self.boundary.workspace,env=env,stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
            start_new_session=True,limit=EXTENSION_POLICY.max_repl_output_bytes*2,
            preexec_fn=self._limits if os.name != "nt" else None,
        )
        async def drain() -> None:
            if process.stderr is None: return
            while await process.stderr.read(8192): pass
        now=time.monotonic()
        return _Process(process=process,stderr_task=asyncio.create_task(drain()),created_at=now,last_activity=now)

    async def execute(self, process: _Process, request: ReplExecuteRequest, session_id: str) -> ReplResult:
        try: validate_code(request.code)
        except ReplPolicyError: return ReplResult(session_id=session_id,status=ReplStatus.FAILED,error_code="repl.policy_denied")
        if process.process.stdin is None or process.process.stdout is None: raise ReplError("REPL process unavailable")
        payload=json.dumps({"code":request.code,"input_data":request.input_data},ensure_ascii=False,separators=(",",":"))+"\n"
        if len(payload.encode()) > EXTENSION_POLICY.max_context_bytes: return ReplResult(session_id=session_id,status=ReplStatus.LIMITED,error_code="repl.input_limit")
        process.process.stdin.write(payload.encode())
        try: await process.process.stdin.drain()
        except (BrokenPipeError,ConnectionResetError) as exc: raise ReplError("REPL process stopped") from exc
        try:
            line=await asyncio.wait_for(process.process.stdout.readline(),timeout=EXTENSION_POLICY.max_repl_seconds)
        except asyncio.TimeoutError:
            await self.stop(process); return ReplResult(session_id=session_id,status=ReplStatus.LIMITED,error_code="repl.timeout")
        if not line or len(line)>EXTENSION_POLICY.max_repl_output_bytes*2:
            await self.stop(process); return ReplResult(session_id=session_id,status=ReplStatus.FAILED,error_code="repl.process_failed")
        try: response=json.loads(line)
        except (TypeError,ValueError): return ReplResult(session_id=session_id,status=ReplStatus.FAILED,error_code="repl.invalid_response")
        process.cells += 1
        try:
            response["status"] = ReplStatus(response["status"])
            return redact_repl_result(ReplResult.model_validate({**response,"session_id":session_id,"trust_mode":"local_trust"}))
        except (TypeError,ValueError): return ReplResult(session_id=session_id,status=ReplStatus.FAILED,error_code="repl.invalid_result")

    async def stop(self, process: _Process) -> None:
        proc=process.process
        if proc.returncode is None:
            try: os.killpg(proc.pid,signal.SIGTERM)
            except (ProcessLookupError,PermissionError): pass
            try: await asyncio.wait_for(proc.wait(),timeout=1)
            except asyncio.TimeoutError:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except (ProcessLookupError,PermissionError): pass
                await proc.wait()
        process.stderr_task.cancel()
        await asyncio.gather(process.stderr_task,return_exceptions=True)

class ReplSessionManager:
    def __init__(self, workspace: str | Path):
        self.runner=ReplRunner(workspace); self._sessions:dict[str,_Process]={}; self._locks:dict[str,asyncio.Lock]={}; self._manager_lock=asyncio.Lock()

    async def _expire_locked(self) -> None:
        now=time.monotonic()
        expired=[sid for sid,process in self._sessions.items() if now-process.last_activity > EXTENSION_POLICY.max_repl_session_seconds]
        for sid in expired:
            process=self._sessions.pop(sid,None); self._locks.pop(sid,None)
            if process is not None: await self.runner.stop(process)

    async def create(self) -> ReplSessionInfo:
        async with self._manager_lock:
            await self._expire_locked()
            if len(self._sessions) >= EXTENSION_POLICY.max_repl_sessions: raise ReplLimitError("REPL session limit exceeded")
            session_id="repl-"+uuid.uuid4().hex
            self._sessions[session_id]=await self.runner.start(); self._locks[session_id]=asyncio.Lock()
            return ReplSessionInfo(session_id=session_id,status="active",cells=0)

    async def execute(self, session_id: str, request: ReplExecuteRequest) -> ReplResult:
        async with self._manager_lock:
            await self._expire_locked()
            process=self._sessions.get(session_id); lock=self._locks.get(session_id)
            if process is None or lock is None: raise ReplError("REPL session unavailable")
            process.last_activity=time.monotonic()
        async with lock:
            if process.cells >= EXTENSION_POLICY.max_repl_cells: return ReplResult(session_id=session_id,status=ReplStatus.LIMITED,error_code="repl.cell_limit")
            result=await self.runner.execute(process,request,session_id)
        process.last_activity=time.monotonic()
        if result.error_code in {"repl.timeout","repl.process_failed","repl.invalid_response"}: await self.interrupt(session_id)
        return result

    async def info(self, session_id: str) -> ReplSessionInfo:
        async with self._manager_lock:
            await self._expire_locked()
            process=self._sessions.get(session_id)
            if process is None: raise ReplError("REPL session unavailable")
            return ReplSessionInfo(session_id=session_id,status="active",cells=process.cells)

    async def interrupt(self, session_id: str) -> None:
        async with self._manager_lock:
            process=self._sessions.pop(session_id,None); self._locks.pop(session_id,None)
        if process is not None: await self.runner.stop(process)

    async def close(self, session_id: str) -> None: await self.interrupt(session_id)

    async def close_all(self) -> None:
        for session_id in tuple(self._sessions): await self.close(session_id)
