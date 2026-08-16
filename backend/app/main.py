"""FastAPI composition root with localhost-only security defaults."""
from __future__ import annotations
import asyncio
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import CAPS
from app.core.security.session import SessionToken
from app.core.security.request import valid_host, valid_origin
from app.core.security.body_limit import BodyLimitMiddleware
from pathlib import Path
from fastapi import Depends
from app.features.graph_authoring.api import router_for
from app.features.graph_authoring.workspace_api import router_for as workspace_router_for
from app.features.graph_authoring.contracts import ForgeGraph
from app.features.graph_authoring.validator import validate_graph
from app.features.execution.engine import GraphRunner
from app.features.execution.api_models import RunRequest
from app.features.execution.services import build_services, ServiceBuildError
from app.features.observability.store import RunStore
from app.features.observability.broker import EventBroker
from app.features.observability.ws_server import WebSocketCommand,WebSocketProtocolError
import uuid
import time
from app.features.retrieval.query import LanceQueryRunner, RetrievalQueryError
from app.features.retrieval.api_models import RetrievalRequest
from app.features.export.generator import export_bundle, package_zip, ExportError
from app.features.export.api_models import ExportRequest
from app.features.providers.contracts import ProviderConfig
from app.features.providers.adapters import DataflowApproval

_ALLOWED_HOSTS={"127.0.0.1","localhost"}
_ALLOWED_ORIGINS={"http://127.0.0.1:5173","http://localhost:5173"}
_ALLOWED_PORTS={None, 80, 443, 5173, 8000}

def create_app(*, session_value: str | None = None, workspace: str | Path | None = None, execution_services=None) -> FastAPI:
    app=FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimitMiddleware,max_bytes=CAPS.max_request_bytes)
    token=SessionToken()
    if session_value is not None: token._value=session_value
    app.state.session_token=token
    app.state.auth_failures=0
    app.state.auth_failure_window=time.monotonic()
    app.state.event_broker=EventBroker()
    @app.exception_handler(RequestValidationError)
    async def validation_exception(request: Request, exc: RequestValidationError):
        status=413 if any(error.get("type")=="string_too_long" and "query" in str(error.get("loc")) for error in exc.errors()) else 422
        response=JSONResponse({"detail":"request too large" if status==413 else "invalid request"},status_code=status)
        response.headers["x-content-type-options"]="nosniff"; response.headers["content-security-policy"]="default-src 'none'; frame-ancestors 'none'"
        return response
    @app.exception_handler(Exception)
    async def generic_exception(request: Request, exc: Exception):
        response=JSONResponse({"detail":"internal server error"},status_code=500)
        response.headers["x-content-type-options"]="nosniff"; response.headers["content-security-policy"]="default-src 'none'; frame-ancestors 'none'"
        return response
    app.add_middleware(CORSMiddleware, allow_origins=sorted(_ALLOWED_ORIGINS), allow_credentials=False, allow_methods=["GET","POST","DELETE"], allow_headers=["content-type","x-harnessforge-token"])
    @app.middleware("http")
    async def localhost_guard(request: Request, call_next):
        raw_host=request.headers.get("host","")
        try: valid=valid_host(raw_host)
        except Exception: valid=False
        if not valid:
            response=JSONResponse({"detail":"invalid host"},status_code=400)
            response.headers["x-content-type-options"]="nosniff"; response.headers["content-security-policy"]="default-src 'none'; frame-ancestors 'none'"
            return response
        origin=request.headers.get("origin")
        content_length=request.headers.get("content-length")
        if content_length and (not content_length.isdigit() or int(content_length) > CAPS.max_request_bytes): response=JSONResponse({"detail":"request too large"},status_code=413)
        elif not valid_host(raw_host): response=JSONResponse({"detail":"invalid host"},status_code=400)
        elif not valid_origin(origin): response=JSONResponse({"detail":"invalid origin"},status_code=400)
        else: response=await call_next(request)
        response.headers["x-content-type-options"]="nosniff"
        response.headers["content-security-policy"]="default-src 'none'; frame-ancestors 'none'"
        return response
    async def auth(x_harnessforge_token: str | None = Header(default=None)):
        now=time.monotonic()
        if now-app.state.auth_failure_window >= 60: app.state.auth_failures=0; app.state.auth_failure_window=now
        if app.state.auth_failures >= CAPS.max_auth_failures: raise HTTPException(status_code=429,detail="authentication temporarily throttled",headers={"retry-after":"60"})
        if not token.verify(x_harnessforge_token):
            app.state.auth_failures=min(CAPS.max_auth_failures, app.state.auth_failures + 1)
            raise HTTPException(status_code=401,detail="unauthorized")
        app.state.auth_failures=0
    app.state.auth_failure_window=time.monotonic()
    app.state.event_broker=EventBroker()
    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        origin=ws.headers.get("origin")
        raw_host=ws.headers.get("host", "")
        host, port = raw_host.rsplit(":", 1) if ":" in raw_host else (raw_host, None)
        valid_port = port is None or (port.isdigit() and int(port) in _ALLOWED_PORTS)
        host=host.casefold()
        candidate=ws.headers.get("x-harnessforge-token")
        if not valid_port or host not in _ALLOWED_HOSTS or origin not in _ALLOWED_ORIGINS:
            await ws.close(code=1008); return
        await ws.accept()
        try:
            header_authenticated=token.verify(candidate)
            if not header_authenticated:
                auth_message=await ws.receive_json()
                candidate=auth_message.get("token") if isinstance(auth_message,dict) and auth_message.get("type")=="auth" else None
            if not token.verify(candidate): await ws.close(code=1008); return
            if not header_authenticated: await ws.send_json({"type":"authenticated"})
            queue=app.state.event_broker.subscribe()
            async def receive_client(): return ("client", await ws.receive_json())
            async def receive_event(): return ("event", await queue.get())
            while True:
                client_task=asyncio.create_task(receive_client()); event_task=asyncio.create_task(receive_event())
                done,pending=await asyncio.wait({client_task,event_task},return_when=asyncio.FIRST_COMPLETED)
                for task in pending: task.cancel()
                kind,payload=next(iter(done)).result()
                if kind=="event": await ws.send_json(payload); continue
                message=payload
                try: command=WebSocketCommand.parse(message)
                except WebSocketProtocolError: await ws.close(code=1003); return
                if command.type == "ping": await ws.send_json({"type":"pong"}); continue
                if command.type == "run.pause":
                    active=getattr(app.state,"active_runner",None)
                    if active is not None: active.pause()
                    await ws.send_json({"type":"run.paused"}); continue
                if command.type == "run.resume":
                    active=getattr(app.state,"active_runner",None)
                    if active is not None: active.resume()
                    await ws.send_json({"type":"run.resumed"}); continue
                if command.type == "run.cancel":
                    active=getattr(app.state,"active_runner",None)
                    if active is not None: active.cancel()
                    await ws.send_json({"type":"run.cancelled"}); continue
                await ws.close(code=1003); return
        except WebSocketDisconnect: return
        finally:
            if "queue" in locals(): app.state.event_broker.unsubscribe(queue)

    @app.post("/api/provider/approval",dependencies=[Depends(auth)])
    async def provider_approval(payload:dict):
        try:
            config=ProviderConfig.model_validate(payload["provider"]); bindings=payload["bindings"]
            if not isinstance(bindings,list) or len(bindings)>32 or any(not isinstance(binding,str) or len(binding)>128 for binding in bindings): raise ValueError
            approval=DataflowApproval.issue(config,bindings)
            return {"approval_fingerprint":approval.fingerprint,"provider":config.kind.value,"bindings":sorted(bindings)}
        except Exception: raise HTTPException(status_code=400,detail="invalid provider approval request")
    @app.post("/api/export",status_code=201,dependencies=[Depends(auth)])
    async def export_graph(request:ExportRequest):
        try:
            graph=request.graph; destination=request.destination
            if graph.settings.review_only: raise ExportError("graph requires activation")
            if not validate_graph(graph).valid: raise ExportError("graph validation failed")
            graph=graph.model_copy(update={"workspace_path":str(Path(workspace or Path.cwd()))})
            files=export_bundle(graph,Path(workspace or Path.cwd()) / destination)
            archive=package_zip(files,Path(workspace or Path.cwd()) / (str(destination).rstrip("/") + ".zip"))
            return {"files":[str(file.relative_to(Path(workspace or Path.cwd()))) for file in files],"archive":str(archive.relative_to(Path(workspace or Path.cwd())))}
        except (KeyError,TypeError,ValueError,ExportError): raise HTTPException(status_code=400,detail="export failed")
    @app.post("/api/retrieval/query", dependencies=[Depends(auth)])
    async def retrieval_query(request:RetrievalRequest):
        try:
            path=request.path; table=request.table; vector=request.vector; top_k=request.top_k
            return {"results":LanceQueryRunner(workspace or Path.cwd()).search(path,table,vector,top_k=top_k)}
        except (KeyError,TypeError,RetrievalQueryError): raise HTTPException(status_code=400,detail="invalid retrieval request")
    async def _run_store():
        store=RunStore(Path(workspace or Path.cwd()) / ".harnessforge" / "runs.db"); await store.initialize(); return store
    @app.post("/api/runs/{run_id}/checkpoints",status_code=201,dependencies=[Depends(auth)])
    async def save_checkpoint(run_id:str,payload:dict):
        try: store=await _run_store();
        except Exception: raise HTTPException(status_code=500,detail="observability unavailable")
        try: await store.create_run(run_id) if not await store.exists_run(run_id) else None; await store.save_checkpoint(run_id,payload["step"],payload.get("payload",{})); return {"accepted":True}
        except Exception: raise HTTPException(status_code=400,detail="invalid checkpoint")
    @app.get("/api/runs",dependencies=[Depends(auth)])
    async def list_runs(limit:int=100,offset:int=0):
        try: return {"runs":await (await _run_store()).list_runs(limit=limit,offset=offset)}
        except ValueError: raise HTTPException(status_code=400,detail="invalid run pagination")
    @app.get("/api/runs/{run_id}/checkpoints",dependencies=[Depends(auth)])
    async def list_checkpoints(run_id:str): return {"checkpoints":await (await _run_store()).list_checkpoints(run_id)}
    @app.post("/api/runs/{run_id}/events",status_code=201,dependencies=[Depends(auth)])
    async def append_run_event(run_id:str,payload:dict):
        from app.features.observability.events import Event
        try: store=await _run_store();
        except Exception: raise HTTPException(status_code=500,detail="observability unavailable")
        try:
            if not await store.exists_run(run_id): await store.create_run(run_id)
            event=Event(type=payload["type"],run_id=run_id,payload=payload.get("payload",{})); await store.append_event(run_id,event); return {"accepted":True}
        except Exception: raise HTTPException(status_code=400,detail="invalid event")
    @app.get("/api/runs/{run_id}/events",dependencies=[Depends(auth)])
    async def list_run_events(run_id:str,limit:int=1000,offset:int=0):
        try: return {"events":[event.model_dump(mode="json") for event in await (await _run_store()).list_events(run_id,limit=limit,offset=offset)]}
        except ValueError: raise HTTPException(status_code=400,detail="invalid pagination")
    @app.delete("/api/runs/{run_id}", status_code=204, dependencies=[Depends(auth)])
    async def delete_run(run_id: str):
        store=RunStore(Path(workspace or Path.cwd()) / ".harnessforge" / "runs.db")
        await store.initialize(); await store.delete_run(run_id)
        return None
    @app.delete("/api/runs", status_code=204, dependencies=[Depends(auth)])
    async def delete_all_runs():
        store=RunStore(Path(workspace or Path.cwd()) / ".harnessforge" / "runs.db")
        await store.initialize(); await store.delete_all()
        return None
    @app.get("/health")
    async def health(): return {"status":"ok"}
    @app.get("/ready")
    async def ready(): return {"status":"ready","localhost_only":True,"telemetry":False}
    app.include_router(router_for(workspace or Path.cwd()), dependencies=[Depends(auth)])
    app.include_router(workspace_router_for(workspace or Path.cwd()), dependencies=[Depends(auth)])
    @app.post("/api/run")
    async def run_graph(request:RunRequest, _: None = Depends(auth)):
        try:
            graph=request.graph; query=request.query
        except Exception: raise HTTPException(status_code=422,detail="invalid run payload")
        if not isinstance(query,str) or len(query.encode()) > 128*1024: raise HTTPException(status_code=413,detail="query too large")
        semantic=validate_graph(graph)
        if not semantic.valid: raise HTTPException(status_code=422,detail="invalid graph validation")
        if graph.settings.review_only: raise HTTPException(status_code=409,detail="graph requires activation")
        try: services=execution_services or build_services(graph, workspace or Path.cwd())
        except ServiceBuildError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
        run_id=uuid.uuid4().hex
        collected=[]
        def sink(event):
            event={**event,"run_id":run_id}; collected.append(event); app.state.event_broker.publish(event)
        runner=GraphRunner(graph, services=services, event_sink=sink); app.state.active_runner=runner
        store=await _run_store(); await store.create_run(run_id)
        try: result=await runner.run(query=query)
        finally:
            app.state.active_runner=None
            provider_clients=[]
            for candidate in [services.provider,*((services.providers or {}).values())]:
                if candidate is not None and candidate not in provider_clients: provider_clients.append(candidate)
            for candidate in provider_clients:
                try: await candidate.aclose()
                except Exception: pass
            status_events={"run.validating":"validating","run.running":"running","run.succeeded":"succeeded","run.failed":"failed","run.cancelled":"cancelled","run.limit_exceeded":"limit_exceeded"}
            for lifecycle_event in collected:
                next_status=status_events.get(lifecycle_event.get("type"))
                if next_status:
                    await store.update_run_status(run_id, next_status)
            if not collected:
                await store.update_run_status(run_id, result.status.value)
            for event in collected:
                try: await store.append_event(run_id, __import__("app.features.observability.events",fromlist=["Event"]).Event(type=event["type"],run_id=run_id,payload={k:v for k,v in event.items() if k not in {"type","run_id"}}))
                except Exception: pass
        code=200 if result.status.value == "succeeded" else 400
        return JSONResponse({"run_id":run_id,"status":result.status.value,"error":result.error,"state":result.state.model_dump(mode="json")},status_code=code)
    @app.get("/api/graph", dependencies=[Depends(auth)])
    async def graph(): return {"nodes":[],"edges":[]}
    return app

app=create_app()
