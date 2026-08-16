"""Bounded concurrent RLM child-agent spawner."""
from __future__ import annotations
import asyncio
from typing import Protocol, Sequence
import uuid
from app.core.extension_contracts import EXTENSION_POLICY
from app.features.rlm.aggregator import aggregate
from app.features.rlm.contracts import AggregateResult, ChildAgentResult, ChildAgentSpec
from app.features.rlm.firewall import child_prompt
from app.features.rlm.policies import RlmPolicyError, validate_spec

class SubAgentPort(Protocol):
    async def execute(self, spec: ChildAgentSpec, prompt: str) -> ChildAgentResult: ...

class RlmSpawner:
    def __init__(self, port: SubAgentPort): self.port=port

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
