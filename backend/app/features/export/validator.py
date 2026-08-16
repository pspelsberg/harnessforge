"""Export-specific validation gate before bundle generation."""
from __future__ import annotations
from pathlib import Path
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
    if graph.settings.review_only: errors.append("review-only graph cannot be exported")
    try: boundary=WorkspaceBoundary(workspace)
    except Exception: errors.append("workspace is invalid"); return ExportValidationResult(tuple(errors),tuple(warnings))
    for node in graph.nodes:
        cfg=node.data.config
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
