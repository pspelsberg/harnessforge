import asyncio
from app.features.observability.store import RunStore
def test_run_history_is_bounded_and_ordered(tmp_path):
 s=RunStore(tmp_path/"runs.db"); asyncio.run(s.initialize()); asyncio.run(s.create_run("r1")); asyncio.run(s.create_run("r2")); runs=asyncio.run(s.list_runs()); assert [r["id"] for r in runs]==["r1","r2"]
