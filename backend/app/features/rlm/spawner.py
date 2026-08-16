"""Bounded concurrent RLM child-agent spawner."""
from __future__ import annotations
import asyncio
import hashlib, json
from typing import Protocol, Sequence
import uuid
from app.core.extension_contracts import EXTENSION_POLICY
from app.features.rlm.aggregator import aggregate
from app.features.rlm.contracts import AggregateResult, ChildAgentResult, ChildAgentSpec
from app.features.rlm.firewall import child_prompt
from app.features.rlm.policies import RlmPolicyError, validate_spec
from app.core.extension_ports import HumanApprovalPort, ApprovalPortError

class SubAgentPort(Protocol):
    async def execute(self, spec: ChildAgentSpec, prompt: str) -> ChildAgentResult: ...

class DisabledSubAgentPort:
    """Fail-closed composition-root adapter until an explicit provider port is configured."""
    async def execute(self, spec: ChildAgentSpec, prompt: str) -> ChildAgentResult:
        return ChildAgentResult(child_run_id="child-disabled-"+uuid.uuid4().hex, parent_run_id=spec.run_id, status="failed", error_code="rlm.disabled")

class RlmSpawner:
    def __init__(self, port: SubAgentPort, approval_port: HumanApprovalPort|None=None): self.port=port; self.approval_port=approval_port
    @staticmethod
    def gate_command(spec: ChildAgentSpec)->str:
        data=spec.model_dump(mode="json"); data.pop("human_gate",None); return "rlm:"+hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()

    async def spawn(self, run_id: str, specs: Sequence[ChildAgentSpec], *, allowed_bindings: set[str]) -> AggregateResult:
        if len(specs)>EXTENSION_POLICY.max_rlm_children: return AggregateResult(run_id=run_id,status="limited",error_code="rlm.child_limit")
        total_tokens=sum(spec.max_tokens for spec in specs)
        if total_tokens>EXTENSION_POLICY.max_rlm_total_tokens: return AggregateResult(run_id=run_id,status="limited",error_code="rlm.token_limit")
        try:
            for spec in specs:
                if spec.run_id != run_id or spec.parent_run_id != run_id: raise RlmPolicyError("cross-run child spec")
                validate_spec(spec,allowed_bindings=allowed_bindings)
        except (RlmPolicyError,ValueError): return AggregateResult(run_id=run_id,status="failed",error_code="rlm.policy_denied")
        semaphore=asyncio.Semaphore(min(len(specs),EXTENSION_POLICY.max_rlm_children))
        async def one(spec: ChildAgentSpec) -> ChildAgentResult:
            async with semaphore:
                try:
                    if spec.requires_human_gate:
                        if spec.human_gate is None or self.approval_port is None: return ChildAgentResult(child_run_id="child-"+uuid.uuid4().hex,parent_run_id=run_id,status="failed",error_code="rlm.approval_required")
                        try: gate=await self.approval_port.consume(spec.human_gate)
                        except ApprovalPortError: return ChildAgentResult(child_run_id="child-"+uuid.uuid4().hex,parent_run_id=run_id,status="failed",error_code="rlm.approval_required")
                        if gate.gate_class!="rlm_spawn" or gate.preview.action!="rlm.spawn" or gate.preview.command!=self.gate_command(spec): return ChildAgentResult(child_run_id="child-"+uuid.uuid4().hex,parent_run_id=run_id,status="failed",error_code="rlm.approval_required")
                    prompt=child_prompt(spec.prompt,spec.context)
                    return await self.port.execute(spec,prompt)
                except asyncio.CancelledError: raise
                except Exception: return ChildAgentResult(child_run_id="child-"+uuid.uuid4().hex,parent_run_id=run_id,status="failed",error_code="rlm.child_failed")
        tasks=[asyncio.create_task(one(spec)) for spec in specs]
        try:
            results=await asyncio.wait_for(asyncio.gather(*tasks),timeout=EXTENSION_POLICY.max_rlm_seconds)
        except asyncio.CancelledError:
            for task in tasks: task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True); raise
        except asyncio.TimeoutError:
            for task in tasks: task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            return AggregateResult(run_id=run_id,status="limited",error_code="rlm.timeout")
        return aggregate(run_id,results)
