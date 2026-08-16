"""Bounded initial scanner that never follows symlinks or crosses WorkspaceBoundary."""
from __future__ import annotations
import hashlib,mimetypes,os,re
from pathlib import Path
from app.core.security.path_sanitizer import WorkspaceBoundary,UnsafePathError
from app.core.security.redaction import redact
from app.core.extension_contracts import EXTENSION_POLICY
from app.features.workspace_indexer.contracts import FileRecord
_ALLOWED={".py",".ts",".tsx",".js",".jsx",".md",".json",".yaml",".yml",".toml",".css",".html"}
_SYMBOL=re.compile(r"^\s*(?:(?:async)\s+)?(?:def|class|function|interface|type|export\s+(?:function|class|interface|type))\s+([A-Za-z_][A-Za-z0-9_]*)",re.MULTILINE)
class ScanError(RuntimeError):pass
class WorkspaceScanner:
 def __init__(self,boundary:WorkspaceBoundary,max_files:int=2048):self.boundary=boundary;self.max_files=max_files
 def scan(self)->list[FileRecord]:
  records=[]
  for root,dirs,files in os.walk(self.boundary.workspace,topdown=True,followlinks=False):
   dirs[:]=[d for d in dirs if d not in {".git",".ssh",".harnessforge"} and not (Path(root)/d).is_symlink()]
   for name in files:
    if len(records)>=self.max_files:raise ScanError("index file cap exceeded")
    path=Path(root)/name
    if path.is_symlink():continue
    try: relative=path.relative_to(self.boundary.workspace).as_posix(); target=self.boundary.resolve(relative,must_exist=True); stat=target.stat()
    except (OSError,ValueError,UnsafePathError):continue
    if name==".env" or target.suffix.lower() not in _ALLOWED or stat.st_size>EXTENSION_POLICY.max_index_file_bytes:continue
    data=target.read_bytes(); digest=hashlib.sha256(data).hexdigest(); mime=mimetypes.guess_type(name)[0] or "text/plain"
    try:
     text=data.decode("utf-8")
     if "\x00" in text:continue
     snippet=redact(text[:8192]); symbols=_SYMBOL.findall(text[:65536]); error=None
    except UnicodeDecodeError: continue
    records.append(FileRecord(relative_path=relative,size=stat.st_size,mime=mime,sha256=digest,mtime_ns=stat.st_mtime_ns,symbols=symbols,snippet=snippet,parser_error=error))
  return records
