"""Export-specific validation gate before bundle generation."""
from __future__ import annotations
from pathlib import Path
import re
from app.features.graph_authoring.validator import validate_graph
from app.features.providers.contracts import ProviderConfig,ProviderKind
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
class ExportValidationError(ValueError): pass
class ExportValidationResult:
    def __init__(self,errors:tuple[str,...],warnings:tuple[str,...]=()): self.errors=errors; self.warnings=warnings
    @property
    def valid(self): return not self.errors
def validate_export(graph,workspace:str|Path)->ExportValidationResult:
    from app.features.graph_authoring.contracts import ForgeGraph
    try: graph=ForgeGraph.model_validate(graph.model_dump(mode="python") if hasattr(graph,"model_dump") else graph)
    except Exception: return ExportValidationResult(("graph contract invalid",))
    errors=[];warnings=[]
    semantic=validate_graph(graph); errors.extend(issue.message for issue in semantic.errors); warnings.extend(issue.message for issue in semantic.issues if issue.severity=="warning")
    outgoing={node.id: [edge for edge in graph.edges if edge.source==node.id] for node in graph.nodes}
    for node in graph.nodes:
        routes=outgoing[node.id]
        if node.type != "output":
            if node.type == "loop":
                handles=[edge.source_handle for edge in routes]
                if len(routes)!=3 or sorted(handles)!=["fallback","false","true"]: errors.append(f"loop routes must be exactly true, false, and fallback for {node.id}")
            elif len(routes)!=1: errors.append(f"node must have exactly one outgoing route for {node.id}")
    if graph.settings.review_only: errors.append("review-only graph cannot be exported")
    try: boundary=WorkspaceBoundary(workspace)
    except Exception: errors.append("workspace is invalid"); return ExportValidationResult(tuple(errors),tuple(warnings))
    for node in graph.nodes:
        cfg=node.data.config
        if node.type=="reducer":
            target=cfg.get("target"); op=cfg.get("op")
            if not isinstance(op,str) or op not in {"SET","APPEND_LIST","MERGE_DICT","INCREMENT"}: errors.append(f"reducer operation invalid for {node.id}")
            if not isinstance(target,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){0,3}",target) or any(part.startswith("__") for part in target.split(".")) or ("." in target and target.split(".")[0] not in {"custom_state","metadata"}) or target in {"custom_state","metadata"}: errors.append(f"reducer target invalid for {node.id}")
        if node.type=="tool":
            if not cfg.get("approved_hash"): errors.append(f"tool approval required for {node.id}")
            try: boundary.resolve(cfg["path"],must_exist=True)
            except (KeyError,UnsafePathError): errors.append(f"tool path invalid for {node.id}")
        if node.type=="rag":
            try: boundary.resolve(cfg["path"],must_exist=True)
            except (KeyError,UnsafePathError): errors.append(f"RAG path invalid for {node.id}")
        if node.type=="llm":
            provider=cfg.get("provider")
            if not isinstance(provider,dict): errors.append(f"provider configuration required for {node.id}"); continue
            try: parsed=ProviderConfig.model_validate(provider)
            except Exception: errors.append(f"provider configuration invalid for {node.id}"); continue
            if parsed.kind in {ProviderKind.OPENAI,ProviderKind.OPENROUTER}:
                if not graph.settings.external_dataflow_activated: errors.append(f"external provider activation required for {node.id}")
                else:
                    bindings=cfg.get("bindings",[]); approval=cfg.get("approval_fingerprint")
                    from app.features.providers.adapters import DataflowApproval
                    if not isinstance(approval,str) or not DataflowApproval(approval).valid_for(parsed,bindings): errors.append(f"provider approval required for {node.id}")
    return ExportValidationResult(tuple(dict.fromkeys(errors)),tuple(dict.fromkeys(warnings)))
