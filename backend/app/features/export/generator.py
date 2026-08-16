"""Atomic, workspace-bounded standalone export pipeline."""
from __future__ import annotations
import json, os, re, tempfile, hashlib
from pathlib import Path
from app.features.graph_authoring.contracts import ForgeGraph
from app.features.graph_authoring.validator import validate_graph
from app.features.export.validator import validate_export
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
class ExportError(ValueError): pass
_SECRET_KEY=re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)")
_CAPS={"max_nodes":50,"max_loop_iterations":50,"max_state_bytes":5*1024*1024,"max_prompt_bytes":128*1024,"max_output_bytes":50*1024}
_TEMPLATE_PATH=Path(__file__).resolve().parents[4]/"templates"/"standalone_runner.py.jinja"
def _reject_secrets(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if _SECRET_KEY.search(str(k)): raise ExportError("secret-like configuration is forbidden in export")
            _reject_secrets(v)
    elif isinstance(value,list):
        for v in value: _reject_secrets(v)
    elif isinstance(value,str) and re.search(r"(?i)(sk-[A-Za-z0-9]|bearer\s+|api[_-]?key\s*[:=])",value): raise ExportError("secret-like value is forbidden in export")
def export_bundle(graph:ForgeGraph,destination:str|Path)->list[Path]:
    validation=validate_export(graph,graph.workspace_path)
    if validation.errors: raise ExportError("export validation failed: "+"; ".join(validation.errors))
    if any(n.type not in {"start","output","reducer","tool","rag","llm","loop"} for n in graph.nodes): raise ExportError("unsupported node for standalone export")
    for node in graph.nodes:
        if node.type=="llm" and not isinstance(node.data.config.get("provider"),dict): raise ExportError("LLM provider configuration required")
        if node.type=="rag" and not all(key in node.data.config for key in ("path","table","vector")): raise ExportError("RAG configuration required")
    for node in graph.nodes:
        if node.type=="tool" and not node.data.config.get("approved_hash"): raise ExportError("tool approval required")
    try:
        boundary=WorkspaceBoundary(graph.workspace_path)
        raw_destination=Path(destination)
        if not raw_destination.is_absolute(): raw_destination=boundary.workspace / raw_destination
        relative=raw_destination.relative_to(boundary.workspace)
        dest=boundary.resolve(relative)
        if dest.exists(): raise ExportError("export destination already exists")
    except ExportError: raise
    except (UnsafePathError,ValueError) as exc: raise ExportError("export destination must be inside workspace") from exc
    data=graph.model_dump(mode="json")
    for node in data.get("nodes",[]):
        if node.get("type") == "tool":
            try:
                tool_path=boundary.resolve(node["data"]["config"]["path"],must_exist=True)
                node["data"]["config"]["script_sha256"]=hashlib.sha256(tool_path.read_bytes()).hexdigest()
            except (KeyError,OSError,UnsafePathError) as exc: raise ExportError("invalid tool path") from exc
    _reject_secrets(data)
    if dest.exists() or dest.is_symlink(): raise ExportError("export destination already exists")
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not _TEMPLATE_PATH.is_file():
        raise ExportError("standalone runner template is unavailable")
    raw_template=_TEMPLATE_PATH.read_text(encoding="utf-8")
    from jinja2 import Environment, StrictUndefined
    try:
        template=Environment(autoescape=False,undefined=StrictUndefined).from_string(raw_template).render(graph_repr=repr(data),caps_repr=repr(_CAPS))
    except Exception as exc:
        raise ExportError("could not render standalone runner template") from exc
    files={"agent_runner.py":template,"requirements.txt":"httpx==0.28.1\nlancedb==0.17.0\npydantic==2.10.6\n",".env.example":"OPENAI_API_KEY=\nOPENROUTER_API_KEY=\n"}
    lock=dest.parent/f".{dest.name}.export-lock"
    try:
        lock_fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except OSError as exc: raise ExportError("export destination is busy") from exc
    try:
        with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
            staging=Path(tmp)/"bundle"; staging.mkdir()
            for name,content in files.items():
                target=staging/name; target.write_text(content); os.chmod(target,0o700 if name=="agent_runner.py" else 0o600)
            # Publish the complete directory in one rename; never expose a partial bundle.
            if dest.exists(): raise ExportError("export destination already exists")
            os.replace(staging, dest)
    except ExportError: raise
    except OSError as exc: raise ExportError("could not publish export bundle") from exc
    finally:
        os.close(lock_fd); Path(lock).unlink(missing_ok=True)
    return [dest/name for name in files]


def package_zip(files:list[Path], destination: str|Path)->Path:
    import zipfile
    destination=Path(destination)
    if destination.suffix != ".zip": raise ExportError("zip destination required")
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists() or destination.is_symlink(): raise ExportError("zip destination already exists")
    names=set()
    lock=destination.parent/f".{destination.name}.export-lock"
    try: lock_fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except OSError as exc: raise ExportError("zip destination is busy") from exc
    try:
        with tempfile.NamedTemporaryFile(prefix=".bundle-",suffix=".zip",dir=destination.parent,delete=False) as temp:
            staged=Path(temp.name)
        try:
            with zipfile.ZipFile(staged,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
                for file in files:
                    if file.name in names or file.is_symlink() or not file.is_file() or file.stat().st_size>2*1024*1024: raise ExportError("invalid bundle file")
                    names.add(file.name); archive.write(file,file.name)
            if destination.exists(): raise ExportError("zip destination already exists")
            os.replace(staged,destination)
        finally: staged.unlink(missing_ok=True)
    except ExportError: raise
    except (OSError,zipfile.BadZipFile) as exc: raise ExportError("could not package bundle") from exc
    finally:
        os.close(lock_fd); Path(lock).unlink(missing_ok=True)
    return destination
