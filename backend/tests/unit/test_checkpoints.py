import asyncio
from app.features.observability.store import RunStore
def test_checkpoint_roundtrip(tmp_path):
 s=RunStore(tmp_path/"runs.db"); asyncio.run(s.initialize()); asyncio.run(s.create_run("r")); asyncio.run(s.save_checkpoint("r",1,{"query":"x"})); assert asyncio.run(s.list_checkpoints("r"))[0]["step"]==1
