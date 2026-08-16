"""Bounded read-only LanceDB vector query use case."""
from __future__ import annotations
from pathlib import Path
from typing import Sequence
from app.core.security.path_sanitizer import WorkspaceBoundary, UnsafePathError
from app.features.retrieval.runner import normalize_results
from app.features.retrieval.inspector import lancedb
class RetrievalQueryError(ValueError): pass
class LanceQueryRunner:
    def __init__(self,workspace:str|Path): self.boundary=WorkspaceBoundary(workspace)
    def search(self,relative:str,table_name:str,vector:Sequence[float],*,top_k:int=5):
        if lancedb is None: raise RetrievalQueryError("LanceDB dependency is unavailable")
        if not vector or len(vector)>4096 or any(not isinstance(x,(int,float)) or isinstance(x,bool) for x in vector): raise RetrievalQueryError("invalid vector")
        if not 1<=top_k<=20: raise RetrievalQueryError("top_k must be between 1 and 20")
        try:
            path=self.boundary.resolve(relative,must_exist=True)
            try: db=lancedb.connect(str(path),read_only=True)
            except (TypeError,ValueError) as first:
                if "read_only" not in str(first): raise
                db=lancedb.connect(str(path))
            table=db.open_table(table_name); rows=table.search(list(vector)).limit(top_k).to_list()
        except (UnsafePathError,ValueError) as exc: raise RetrievalQueryError("invalid retrieval request") from exc
        except Exception as exc: raise RetrievalQueryError("retrieval failed") from exc
        return normalize_results(rows,top_k=top_k)
