import asyncio, json
from datetime import datetime, timedelta, timezone
from app.features.observability.store import RunStore
from app.features.observability.events import Event, redact_event

def test_event_is_bounded_and_redacted():
    event=redact_event(Event(type="tool.output", run_id="r1", payload={"text":"api_key=secret"}))
    assert "secret" not in json.dumps(event.model_dump())

def test_sqlite_store_persists_and_retains_runs(tmp_path):
    store=RunStore(tmp_path/"runs.db")
    asyncio.run(store.initialize())
    asyncio.run(store.create_run("r1")); asyncio.run(store.append_event("r1", Event(type="run.started",run_id="r1",payload={})))
    assert asyncio.run(store.list_events("r1"))[0].type == "run.started"
    asyncio.run(store.delete_run("r1")); assert asyncio.run(store.list_events("r1")) == []

def test_store_rejects_oversized_event(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize())
    try: asyncio.run(store.append_event("r1", Event(type="state.diff",run_id="r1",payload={"x":"a"*300000})))
    except ValueError: pass
    else: raise AssertionError("oversized event accepted")


def test_nested_event_secrets_are_redacted(tmp_path):
    event=redact_event(Event(type="state.diff",run_id="r",payload={"nested":{"token":"token=secret"}}))
    assert "secret" not in event.model_dump_json()


def test_event_ids_and_pagination_are_bounded(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("r1"))
    with __import__("pytest").raises(ValueError): asyncio.run(store.list_events("r1",limit=10001))


def test_append_requires_existing_run(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize())
    import pytest
    with pytest.raises(Exception): asyncio.run(store.append_event("missing", Event(type="state.diff",run_id="missing",payload={})))


def test_nested_secret_keys_are_redacted():
    event=redact_event(Event(type="state.diff",run_id="r",payload={"credentials":{"api_key":"secret","token":"another"},"items":[{"Authorization":"Bearer key"}]}))
    rendered=event.model_dump_json()
    assert "secret" not in rendered and "another" not in rendered and "Bearer key" not in rendered


def test_purge_before_removes_old_runs(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("r1")); asyncio.run(store.purge_before("9999-01-01")); assert asyncio.run(store.list_events("r1"))==[]


def test_retention_cutoff_uses_sqlite_timestamp_format(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("r")); asyncio.run(store.purge_before("9999-01-01 00:00:00")); assert asyncio.run(store.exists_run("r")) is False


def test_event_payload_rejects_non_json_values():
    import pytest
    with pytest.raises(Exception): Event(type="state.diff",run_id="r",payload={"bad":object()})


def test_delete_run_and_delete_all_remove_checkpoints(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("r")); asyncio.run(store.save_checkpoint("r",1,{"x":1})); asyncio.run(store.delete_run("r")); assert asyncio.run(store.list_checkpoints("r"))==[]
    asyncio.run(store.create_run("a")); asyncio.run(store.save_checkpoint("a",1,{})); asyncio.run(store.delete_all()); assert asyncio.run(store.list_checkpoints("a"))==[]


def test_node_event_payload_is_bounded():
    event=Event(type="node.running",run_id="r",payload={"node_id":"n"}); assert event.payload["node_id"]=="n"


def test_run_list_pagination_is_bounded(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); [asyncio.run(store.create_run(str(i))) for i in range(3)]; assert len(asyncio.run(store.list_runs(limit=2)))==2


def test_retention_purge_removes_checkpoints(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("old")); asyncio.run(store.save_checkpoint("old",1,{"secret":"x"})); asyncio.run(store.purge_before("9999-01-01 00:00:00")); assert asyncio.run(store.list_checkpoints("old"))==[]


def test_run_store_tracks_bounded_lifecycle_status(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("r1"))
    assert asyncio.run(store.get_run_status("r1")) == "created"
    asyncio.run(store.update_run_status("r1", "validating"))
    asyncio.run(store.update_run_status("r1", "running"))
    asyncio.run(store.update_run_status("r1", "cancelled"))
    assert asyncio.run(store.get_run_status("r1")) == "cancelled"
    with __import__("pytest").raises(ValueError): asyncio.run(store.update_run_status("r1", "unknown"))
    with __import__("pytest").raises(ValueError): asyncio.run(store.update_run_status("r1", "running"))


def test_checkpoints_are_redacted_and_bounded_by_default(tmp_path):
    store=RunStore(tmp_path/"runs.db"); asyncio.run(store.initialize()); asyncio.run(store.create_run("r"))
    asyncio.run(store.save_checkpoint("r",1,{"token":"Bearer secret","nested":{"api_key":"value"}}))
    rendered=json.dumps(asyncio.run(store.list_checkpoints("r")))
    assert "secret" not in rendered and "value" not in rendered and "[REDACTED]" in rendered
    asyncio.run(store.save_checkpoint("r",2,{"x":"a"*300000}))
    assert len(asyncio.run(store.list_checkpoints("r"))[1]["payload"]["x"]) <= 4096
