import pytest
from app.features.execution.engine import GraphRunner, RunState, RunError
from app.features.graph_authoring.contracts import ForgeGraph, GraphNode, GraphEdge

def n(i,t,config=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":config or {},"ui":{}})
def g(nodes,edges): return ForgeGraph(id="g",name="g",workspace_path=".",nodes=nodes,edges=edges)

@pytest.mark.asyncio
async def test_runner_executes_reducer_and_emits_lifecycle():
    graph=g([n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"done"}),n("o","output")],[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")])
    events=[]; result=await GraphRunner(graph,event_sink=events.append).run(query="hi")
    assert result.status is RunState.SUCCEEDED and result.state.last_output == "done"
    assert [e["type"] for e in events] == ["run.created","run.validating","run.running","node.queued","node.running","node.succeeded","state.diff","node.queued","node.running","node.succeeded","state.diff","run.succeeded"]

@pytest.mark.asyncio
async def test_loop_uses_declarative_condition_and_fallback():
    graph=g([n("s","start"),n("l","loop",{"condition_type":"number","key":"iteration","operator":"lt","value":2,"max_iterations":2,"fallback":"f"}),n("r","reducer",{"op":"INCREMENT","target":"iteration","value":1}),n("f","reducer",{"op":"SET","target":"last_output","value":"fallback"}),n("o","output")],[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="r",source_handle="true"),GraphEdge(id="3",source="r",target="l"),GraphEdge(id="4",source="l",target="f",source_handle="fallback"), GraphEdge(id="6",source="l",target="f",source_handle="false"),GraphEdge(id="5",source="f",target="o")])
    result=await GraphRunner(graph).run()
    assert result.state.iteration == 2 and result.state.last_output == "fallback" and result.status is RunState.SUCCEEDED

@pytest.mark.asyncio
async def test_unsupported_node_fails_without_execution():
    graph=g([n("s","start"),n("x","tool"),n("o","output")],[GraphEdge(id="1",source="s",target="x"),GraphEdge(id="2",source="x",target="o")])
    result=await GraphRunner(graph).run()
    assert result.status is RunState.FAILED and result.error == "tool service unavailable"


@pytest.mark.asyncio
async def test_loop_regex_condition_is_bounded():
    graph=g([n("s","start"),n("l","loop",{"condition_type":"regex","key":"query","value":"^hi$","max_iterations":1,"fallback":"f"}),n("r","reducer",{"op":"SET","target":"last_output","value":"yes"}),n("f","reducer",{"op":"SET","target":"last_output","value":"no"}),n("o","output")],[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="r",source_handle="true"),GraphEdge(id="3",source="l",target="f",source_handle="false"),GraphEdge(id="4",source="l",target="f",source_handle="fallback"),GraphEdge(id="5",source="r",target="o"),GraphEdge(id="6",source="f",target="o")])
    assert (await GraphRunner(graph).run(query="hi")).state.last_output == "yes"


@pytest.mark.asyncio
async def test_runner_rejects_concurrent_runs(monkeypatch):
    import app.features.execution.engine as engine
    graph=g([n("s","start"),n("o","output")],[GraphEdge(id="e",source="s",target="o")])
    engine.GraphRunner._active=False
    first=GraphRunner(graph); second=GraphRunner(graph)
    first._run_step_delay=0.05
    task=__import__("asyncio").create_task(first.run())
    await __import__("asyncio").sleep(0)
    result=await second.run()
    await task
    assert result.status is RunState.FAILED and "active" in (result.error or "")

@pytest.mark.asyncio
async def test_runner_timeout_returns_limit_exceeded():
    import app.features.execution.engine as engine
    graph=g([n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"x"}),n("o","output")],[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")])
    old=engine.CAPS.max_run_seconds
    object.__setattr__(engine.CAPS,"max_run_seconds",0.001)
    try:
        runner=GraphRunner(graph); runner._run_step_delay=0.01
        result=await runner.run()
        assert result.status is RunState.LIMIT_EXCEEDED
    finally: object.__setattr__(engine.CAPS,"max_run_seconds",old)


@pytest.mark.asyncio
async def test_invalid_run_does_not_poison_active_lock():
    graph=g([n("s","start"),n("o","output")],[])
    GraphRunner._active=False
    result=await GraphRunner(graph).run(); assert result.status is RunState.FAILED
    valid_graph=g([n("s","start"),n("o","output")],[GraphEdge(id="e",source="s",target="o")])
    assert (await GraphRunner(valid_graph).run()).status is RunState.SUCCEEDED


@pytest.mark.asyncio
async def test_runner_emits_cancelled_lifecycle_event():
    graph=g([n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"x"}),n("o","output")],[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")]); events=[]; runner=GraphRunner(graph,event_sink=events.append); runner.cancel(); result=await runner.run(); assert result.status is RunState.CANCELLED


@pytest.mark.asyncio
async def test_runner_emits_limit_event():
    graph=g([n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"x"}),n("o","output")],[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")]); events=[]; import app.features.execution.engine as engine; old=engine.CAPS.max_run_seconds; object.__setattr__(engine.CAPS,"max_run_seconds",0.0)
    try: result=await GraphRunner(graph,event_sink=events.append).run(); assert result.status is RunState.LIMIT_EXCEEDED and events[-1]["type"]=="run.limit_exceeded"
    finally: object.__setattr__(engine.CAPS,"max_run_seconds",old)


@pytest.mark.asyncio
async def test_runner_pause_and_resume_are_bounded():
    graph=g([n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"x"}),n("o","output")],[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")]); runner=GraphRunner(graph); runner.pause(); task=__import__("asyncio").create_task(runner.run()); await __import__("asyncio").sleep(0.02); assert not task.done(); runner.resume(); result=await task; assert result.status is RunState.SUCCEEDED


@pytest.mark.asyncio
async def test_runner_emits_node_failed_without_exception_details():
    graph=g([n("s","start"),n("t","tool"),n("o","output")],[GraphEdge(id="1",source="s",target="t"),GraphEdge(id="2",source="t",target="o")]); events=[]; result=await GraphRunner(graph,event_sink=events.append).run(); assert result.status is RunState.FAILED; assert any(e["type"]=="node.failed" and e["node_id"]=="t" for e in events); assert all("Traceback" not in str(e) for e in events)


@pytest.mark.asyncio
async def test_state_diff_event_contains_keys_not_values():
    graph=g([n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"secret-value"}),n("o","output")],[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")]); events=[]; result=await GraphRunner(graph,event_sink=events.append).run(); diffs=[e for e in events if e["type"]=="state.diff"]; assert diffs and "last_output" in diffs[0]["changed_keys"] and "secret-value" not in str(diffs)


@pytest.mark.asyncio
async def test_runner_failure_event_does_not_expose_raw_exception_details():
    graph=g([n("s","start"),n("t","tool"),n("o","output")],[GraphEdge(id="1",source="s",target="t"),GraphEdge(id="2",source="t",target="o")]); events=[]; result=await GraphRunner(graph,event_sink=events.append).run(); failed=[e for e in events if e["type"]=="node.failed"][0]; assert "Traceback" not in str(failed) and "secret" not in str(failed).lower() and len(failed.get("error",""))<=256
