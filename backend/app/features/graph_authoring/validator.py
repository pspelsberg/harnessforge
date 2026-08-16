"""Semantic graph validation; no execution occurs in this slice."""
from __future__ import annotations
from dataclasses import dataclass
from app.features.graph_authoring.contracts import ForgeGraph

@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    node_id: str | None = None

@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]
    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")
    @property
    def valid(self) -> bool:
        return not self.errors

def validate_graph(graph: ForgeGraph) -> ValidationResult:
    issues: list[ValidationIssue] = []
    ids = {n.id for n in graph.nodes}
    outgoing = {node_id: [] for node_id in ids}
    for edge in graph.edges:
        outgoing[edge.source].append(edge.target)
    start = next(n for n in graph.nodes if n.type == "start")
    reachable: set[str] = set()
    stack = [start.id]
    while stack:
        current = stack.pop()
        if current in reachable: continue
        reachable.add(current); stack.extend(outgoing[current])
    # A back-edge is permitted only when the cycle contains an explicit loop node.
    node_types = {node.id: node.type for node in graph.nodes}
    visiting: list[str] = []
    visited: set[str] = set()
    def walk(current: str) -> None:
        if current in visiting:
            cycle = visiting[visiting.index(current):]
            if not any(node_types[n] == "loop" for n in cycle):
                issues.append(ValidationIssue("error", "UNGOVERNED_CYCLE", "cycles require a loop node", current))
            return
        if current in visited:
            return
        visiting.append(current)
        for target in outgoing[current]:
            walk(target)
        visiting.pop()
        visited.add(current)
    walk(start.id)
    for node in graph.nodes:
        if node.id not in reachable:
            issues.append(ValidationIssue("error", "UNREACHABLE_NODE", "node is unreachable", node.id))
    for node in graph.nodes:
        if node.type == "loop":
            config = node.data.config
            maximum = config.get("max_iterations")
            if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 50:
                issues.append(ValidationIssue("error", "INVALID_LOOP_LIMIT", "loop max_iterations must be 1..50", node.id))
            fallback=config.get("fallback")
            if not isinstance(fallback,str) or not fallback or not any(target == fallback and handle == "fallback" for target,handle in [(e.target,e.source_handle) for e in graph.edges if e.source == node.id]):
                issues.append(ValidationIssue("error", "MISSING_LOOP_FALLBACK", "loop requires a valid fallback route", node.id))
            branch_handles={e.source_handle for e in graph.edges if e.source == node.id}
            if not {"true","false"}.issubset(branch_handles):
                issues.append(ValidationIssue("error", "MISSING_LOOP_BRANCH", "loop requires true and false routes", node.id))
            if config.get("condition_type") not in {"equals", "regex", "number", "exists"}:
                issues.append(ValidationIssue("error", "INVALID_LOOP_CONDITION", "loop condition is not declarative", node.id))
    if not any(n.type == "output" and n.id in reachable for n in graph.nodes):
        issues.append(ValidationIssue("error", "OUTPUT_UNREACHABLE", "output is unreachable"))
    for node in graph.nodes:
        config=node.data.config
        path=config.get("path") if node.type in {"rag","tool"} else None
        if path is not None and (not isinstance(path,str) or not path): issues.append(ValidationIssue("error","INVALID_REFERENCE","referenced path must be a non-empty string",node.id))
        if node.type=="llm" and not config.get("provider"): issues.append(ValidationIssue("warning","MISSING_PROVIDER","LLM node has no provider configured",node.id))
        if node.type=="rag" and (not isinstance(config.get("path"),str) or not isinstance(config.get("table"),str) or not isinstance(config.get("vector"),list) or not config.get("vector")): issues.append(ValidationIssue("error","INVALID_RAG_CONFIG","RAG requires path, table, and vector",node.id))
        if node.type=="llm" and ("temperature" in config and (not isinstance(config.get("temperature"),(int,float)) or not 0<=config.get("temperature")<=2)): issues.append(ValidationIssue("error","INVALID_LLM_CONFIG","LLM temperature must be 0..2",node.id))
        if node.type=="tool" and ("timeout_seconds" in config and (not isinstance(config.get("timeout_seconds"),(int,float)) or not 0<config.get("timeout_seconds")<=60)): issues.append(ValidationIssue("error","INVALID_TOOL_CONFIG","tool timeout must be 0..60",node.id))
        if node.type=="tool" and ("args" in config and (not isinstance(config.get("args"),list) or len(config.get("args"))>32 or any(not isinstance(arg,str) or len(arg)>1024 for arg in config.get("args")))): issues.append(ValidationIssue("error","INVALID_TOOL_CONFIG","tool args are bounded strings",node.id))
        if node.type=="reducer" and config.get("op") not in {"SET","APPEND_LIST","MERGE_DICT","INCREMENT"}: issues.append(ValidationIssue("error","INVALID_REDUCER_CONFIG","unsupported reducer operation",node.id))
    return ValidationResult(tuple(issues))
