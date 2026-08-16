"""Deterministic bounded graph interpreter for the foundation runtime."""
from __future__ import annotations
import asyncio
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable
from app.core.config import CAPS
from app.features.graph_authoring.contracts import ForgeGraph, GraphNode
from app.features.graph_authoring.validator import validate_graph
from app.features.execution.state import AgentState, Reducer, ReducerOp, apply_reducer
from app.features.execution.ports import ExecutionServices
from app.features.retrieval.context import UntrustedContext, format_untrusted_context, UNTRUSTED_CONTEXT_SYSTEM_INSTRUCTION

class RunState(StrEnum): CREATED="created"; VALIDATING="validating"; RUNNING="running"; SUCCEEDED="succeeded"; FAILED="failed"; CANCELLED="cancelled"; LIMIT_EXCEEDED="limit_exceeded"
class RunError(RuntimeError): pass
@dataclass(frozen=True)
class RunResult: status: RunState; state: AgentState; error: str | None = None

class GraphRunner:
    _active=False
    def __init__(self, graph: ForgeGraph, *, event_sink: Callable[[dict[str, Any]], None] | None = None, services: ExecutionServices | None = None) -> None:
        self.graph=graph; self.event_sink=event_sink or (lambda event: None); self.services=services or ExecutionServices(); self._cancelled=False; self._paused=False; self._resume_event=asyncio.Event(); self._resume_event.set(); self._run_step_delay=0.0
        self.nodes={n.id:n for n in graph.nodes}; self.out={n.id:[] for n in graph.nodes}
        for edge in graph.edges: self.out[edge.source].append((edge.target,edge.source_handle))
    def cancel(self) -> None: self._cancelled=True
    def pause(self) -> None: self._paused=True; self._resume_event.clear(); self._event("run.paused")
    def resume(self) -> None: self._paused=False; self._resume_event.set(); self._event("run.resumed")
    def _event(self, kind: str, **data: Any) -> None: self.event_sink({"type":kind,**data})
    async def run(self, *, query: str = "") -> RunResult:
        state=AgentState(query=query)
        if type(self)._active: return RunResult(RunState.FAILED,state,"another run is active")
        type(self)._active=True
        started=asyncio.get_running_loop().time()
        self._event("run.created")
        self._event("run.validating")
        validation=validate_graph(self.graph)
        if not validation.valid:
            error="; ".join(i.message for i in validation.errors)
            self._event("run.failed", error=error[:256])
            self._event("run.completed", status=RunState.FAILED.value)
            type(self)._active=False
            return RunResult(RunState.FAILED,state,error)
        self._event("run.running"); current=next(n.id for n in self.graph.nodes if n.type=="start"); steps=0; loop_counts: dict[str,int]={}
        try:
            while self.nodes[current].type != "output":
                await self._resume_event.wait()
                if self._cancelled:
                    self._event("run.cancelled"); self._event("run.completed", status=RunState.CANCELLED.value); return RunResult(RunState.CANCELLED,state,"cancelled")
                if asyncio.get_running_loop().time() - started > CAPS.max_run_seconds:
                    self._event("run.limit_exceeded"); self._event("run.completed", status=RunState.LIMIT_EXCEEDED.value); return RunResult(RunState.LIMIT_EXCEEDED,state,"run timeout exceeded")
                if steps >= CAPS.max_nodes * CAPS.max_loop_iterations:
                    self._event("run.limit_exceeded"); self._event("run.completed", status=RunState.LIMIT_EXCEEDED.value); return RunResult(RunState.LIMIT_EXCEEDED,state,"run step limit exceeded")
                node=self.nodes[current]; self._event("node.queued",node_id=node.id); self._event("node.running",node_id=node.id); steps += 1
                targets=self.out[node.id]
                if node.type in {"start","reducer"}:
                    if node.type=="reducer": apply_reducer(state, Reducer.model_validate(node.data.config))
                    current=self._choose(targets, None)
                elif node.type == "rag":
                    retrieval=(self.services.retrievals or {}).get(node.id,self.services.retrieval)
                    if retrieval is None: raise RunError("retrieval service unavailable")
                    cfg=node.data.config; rows=retrieval.search(cfg["path"],cfg["table"],cfg["vector"],top_k=cfg.get("top_k",5))
                    state.retrieved_context.extend(rows); current=self._choose(targets,None)
                elif node.type == "llm":
                    provider=(self.services.providers or {}).get(node.id,self.services.provider)
                    if provider is None: raise RunError("provider service unavailable")
                    from app.features.providers.adapters import ProviderRequest
                    from app.features.providers.prompt_binding import interpolate_prompt,compose_prompt
                    cfg=node.data.config
                    template=cfg.get("node_prompt","{query}")
                    if cfg.get("prompt_file") and self.services.prompt_loader is not None: template=self.services.prompt_loader.load(cfg["prompt_file"])
                    prompt=compose_prompt(global_prompt=str(cfg.get("global_prompt","")),local_prompt=str(cfg.get("local_prompt","")),node_prompt=template,state=state.model_dump(mode="json"))
                    if state.retrieved_context:
                        contexts=[UntrustedContext(text=str(item.get("text","")),score=float(item.get("score",0.0)),metadata=item.get("metadata",{})) for item in state.retrieved_context]
                        prompt += "\n" + format_untrusted_context(contexts)
                    chunks=[]
                    approval=(self.services.approvals or {}).get(node.id,self.services.provider_approval); bindings=(self.services.bindings or {}).get(node.id,self.services.provider_bindings or [])
                    async for chunk in provider.complete(ProviderRequest(messages=[{"role":"system","content":UNTRUSTED_CONTEXT_SYSTEM_INSTRUCTION},{"role":"user","content":prompt}]),approval=approval,bindings=bindings): chunks.append(chunk.text)
                    state.last_output="".join(chunks); current=self._choose(targets,None)
                elif node.type == "tool":
                    tool=(self.services.tools or {}).get(node.id,self.services.tool)
                    if tool is None: raise RunError("tool service unavailable")
                    cfg=node.data.config
                    from app.features.tool_execution.runner import ToolSpec
                    spec=ToolSpec(path=cfg["path"],args=cfg.get("args",[]),timeout_seconds=cfg.get("timeout_seconds",15),allowed_write_dirs=cfg.get("allowed_write_dirs",[]),env_allowlist=cfg.get("env_allowlist",[]))
                    approved=cfg.get("approved_hash", "")
                    if not approved and hasattr(tool,"config_hash"): approved=tool.config_hash(spec)
                    result=await tool.run(spec,approved_hash=approved); state.tool_results.append({"stdout":result.stdout,"stderr":result.stderr,"returncode":result.returncode}); state.last_output=result.stdout; current=self._choose(targets,None)
                elif node.type=="loop":
                    count=loop_counts.get(node.id,0); cfg=node.data.config; maximum=cfg["max_iterations"]
                    if count >= maximum:
                        state.iteration = count
                        current=self._choose(targets,"fallback")
                    else:
                        loop_counts[node.id]=count+1; state.iteration=count
                        current=self._choose(targets,"true" if self._condition(state,cfg) else "false")
                else: raise RunError(f"unsupported node type: {node.type}")
                self._event("node.succeeded",node_id=node.id)
                self._event("state.diff",changed_keys=["last_output","iteration","retrieved_context","tool_results"])
                await asyncio.sleep(self._run_step_delay)
            self._event("run.succeeded"); self._event("run.completed", status=RunState.SUCCEEDED.value); return RunResult(RunState.SUCCEEDED,state)
        except Exception as exc:
            safe_error=str(exc).splitlines()[0][:256] if isinstance(exc,RunError) else "execution failed"
            self._event("node.failed",node_id=node.id if "node" in locals() else None,error=safe_error)
            self._event("run.failed"); self._event("run.completed", status=RunState.FAILED.value); return RunResult(RunState.FAILED,state,safe_error)
        finally:
            type(self)._active=False
    @staticmethod
    def _choose(targets: list[tuple[str,str|None]], handle: str|None) -> str:
        for target, source_handle in targets:
            if source_handle == handle: return target
        if handle is None and len(targets)==1: return targets[0][0]
        raise RunError(f"missing route: {handle}")
    @staticmethod
    def _condition(state: AgentState, cfg: dict[str, Any]) -> bool:
        key = cfg.get("key", "iteration")
        actual: Any = state.model_dump(mode="python")
        found = True
        for part in key.split(".") if isinstance(key, str) else ():
            if not isinstance(actual, dict) or part not in actual:
                found = False
                actual = None
                break
            actual = actual[part]
        expected = cfg.get("value")
        condition_type = cfg.get("condition_type")
        if condition_type == "exists":
            return found
        if condition_type == "equals":
            return actual == expected
        if condition_type == "number":
            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or isinstance(expected, bool) or not isinstance(expected, (int, float)):
                return False
            operator = cfg.get("operator", "gt")
            return {
                "lt": actual < expected, "lte": actual <= expected,
                "gt": actual > expected, "gte": actual >= expected,
                "eq": actual == expected, "ne": actual != expected,
            }.get(operator, False)
        if condition_type == "regex":
            if not isinstance(actual, str) or not isinstance(expected, str) or len(expected) > 256:
                return False
            try:
                return re.search(expected, actual[:8192]) is not None
            except re.error:
                return False
        return False
