"""Bounded aggregation of child-agent projections."""
from __future__ import annotations
from app.core.extension_contracts import EXTENSION_POLICY
from app.features.rlm.contracts import AggregateResult, ChildAgentResult
from app.features.rlm.firewall import aggregate_result

def aggregate(run_id: str, results: list[ChildAgentResult]) -> AggregateResult:
    if len(results)>EXTENSION_POLICY.max_rlm_children: return AggregateResult(run_id=run_id,status="limited",error_code="rlm.child_limit")
    if len({item.child_run_id for item in results}) != len(results): return AggregateResult(run_id=run_id,status="failed",error_code="rlm.invalid_child_result")
    try: safe=[aggregate_result(item,run_id) for item in results]
    except (AttributeError,TypeError,ValueError): return AggregateResult(run_id=run_id,status="failed",error_code="rlm.invalid_child_result")
    if any(item.status=="cancelled" for item in safe): status="cancelled"
    elif any(item.status=="limited" for item in safe): status="limited"
    elif any(item.status=="failed" for item in safe): status="failed"
    else: status="succeeded"
    summary="\n".join(f"child {item.child_run_id}: {item.summary}" for item in safe)[:16*1024]
    return AggregateResult(run_id=run_id,status=status,children=safe,summary=summary,error_code=None if status=="succeeded" else f"rlm.{status}")
