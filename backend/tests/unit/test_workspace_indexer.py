import os,time
from pathlib import Path
import pytest
from app.features.workspace_indexer.contracts import IndexQuery
from app.features.workspace_indexer.scanner import WorkspaceScanner
from app.features.workspace_indexer.service import IndexerError,WorkspaceIndexService
from app.features.workspace_indexer.watcher import ChangeQueue

@pytest.mark.asyncio
async def test_indexer_boundary_excludes_symlink_binary_sensitive_and_large(tmp_path):
 (tmp_path/"src").mkdir();(tmp_path/"src/main.py").write_text("class Demo:\n def run(self): pass\n");(tmp_path/".env").write_text("TOKEN=secret");(tmp_path/".git").mkdir();(tmp_path/".git/x.py").write_text("class Hidden: pass");(tmp_path/"src/binary.py").write_bytes(b"\x00\x01");(tmp_path/"src/large.py").write_bytes(b"x"*(2*1024*1024+1)); outside=tmp_path.parent/"outside.py";outside.write_text("class Outside: pass");(tmp_path/"src/link.py").symlink_to(outside)
 records=WorkspaceScanner(__import__("app.core.security.path_sanitizer",fromlist=["WorkspaceBoundary"]).WorkspaceBoundary(tmp_path)).scan();paths={r.relative_path for r in records};assert "src/main.py" in paths and not any(x in paths for x in [".env","src/binary.py","src/large.py","src/link.py",".git/x.py"]);assert records[0].symbols

@pytest.mark.asyncio
async def test_index_rebuild_is_versioned_read_only_and_query_escapes_like(tmp_path):
 (tmp_path/"agents.md").write_text("Refiner safe text")
 service=WorkspaceIndexService(tmp_path);job=await service.rebuild("session-1",str(tmp_path.resolve()));assert job.version==1;result=await service.query(IndexQuery(session_id="session-1",query="Refiner"));assert result.context_label=="untrusted_workspace_context" and len(result.results)==1
 wildcard=await service.query(IndexQuery(session_id="session-1",query="%"));assert wildcard.results==[]
 with pytest.raises(IndexerError):await service.rebuild("session-1",str(tmp_path.parent))
 await service.pause();assert (await service.status()).status=="paused"
 with pytest.raises(IndexerError):await service.rebuild("session-1",str(tmp_path.resolve()))
 await service.resume();assert (await service.status()).status=="idle"

def test_change_queue_is_bounded_and_debounced():
 queue=ChangeQueue(max_items=2,debounce_seconds=0.01);assert queue.enqueue("a") and not queue.enqueue("a") and queue.enqueue("b") and not queue.enqueue("c");time.sleep(.02);assert queue.drain()==["a","b"]
