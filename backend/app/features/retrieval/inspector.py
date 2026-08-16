"""Read-only LanceDB inspection bounded by the selected workspace."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
try:
    import lancedb
except ImportError:  # optional until a workspace actually configures LanceDB
    lancedb=None
class RetrievalError(ValueError): pass
class LanceInspector:
    def __init__(self,workspace:str|Path): self.boundary=WorkspaceBoundary(workspace)
    def _db(self,relative:str):
        if lancedb is None: raise RetrievalError("LanceDB dependency is unavailable")
        try: path=self.boundary.resolve(relative,must_exist=True)
        except UnsafePathError as exc: raise RetrievalError("database path is outside workspace") from exc
        if not path.is_dir(): raise RetrievalError("database path is not a directory")
        try: return lancedb.connect(str(path),read_only=True)
        except (TypeError,ValueError) as first:
            if "read_only" not in str(first): raise RetrievalError("could not open LanceDB") from first
            try: return lancedb.connect(str(path))
            except Exception as exc: raise RetrievalError("could not open LanceDB") from exc
        except Exception as exc: raise RetrievalError("could not open LanceDB") from exc
    def list_tables(self,relative:str)->list[str]:
        try: names=list(self._db(relative).table_names())
        except RetrievalError: raise
        except Exception as exc: raise RetrievalError("could not list LanceDB tables") from exc
        if len(names)>200 or any(not isinstance(name,str) or len(name)>128 for name in names): raise RetrievalError("invalid table metadata")
        return names
    def describe(self,relative:str,table_name:str)->dict[str,Any]:
        if not isinstance(table_name,str) or not table_name or len(table_name)>128 or table_name not in self.list_tables(relative): raise RetrievalError("unknown table")
        try:
            raw_schema=self._db(relative).open_table(table_name).schema
            schema=raw_schema() if callable(raw_schema) else raw_schema
        except Exception as exc: raise RetrievalError("could not inspect table") from exc
        if isinstance(schema,dict): fields=schema.get("fields",[])
        else:
            raw_names=getattr(schema,"names",[]); fields=raw_names() if callable(raw_names) else raw_names
        names=[field.get("name") if isinstance(field,dict) else str(field) for field in fields] if isinstance(fields,(list,tuple)) else list(fields)
        text_column=next((name for name in names if name in {"text","content","document"}),None)
        vector_column=next((name for name in names if name in {"vector","embedding"}),None)
        return {"table":table_name,"columns":names,"text_column":text_column,"vector_column":vector_column}
