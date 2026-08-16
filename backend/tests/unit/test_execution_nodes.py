import pytest
from app.features.execution.engine import GraphRunner, RunState
from app.features.execution.state import AgentState
from app.features.execution.ports import ExecutionServices
from app.features.graph_authoring.contracts import ForgeGraph, GraphNode, GraphEdge

def n(i,t,c=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
def g(nodes,edges): return ForgeGraph(id="g",name="g",workspace_path=".",settings={"review_only":False,"external_dataflow_activated":True},nodes=nodes,edges=edges)
class FakeProvider:
    async def complete(self,request,**kwargs):
        yield type("Chunk",(),{"text":"answer","finish_reason":"stop"})()
class FakeRetrieval:
    def search(self,path,table,vector,top_k=5): return [{"text":"doc","score":0.1,"metadata":{"source":"test"}}]
class FakeTool:
    async def run(self,spec,approved_hash): return type("Result",(),{"returncode":0,"stdout":"tool-ok","stderr":"","timed_out":False,"trust_mode":"local_trust_mode"})()

@pytest.mark.asyncio
async def test_runner_dispatches_llm_rag_and_tool_nodes():
    graph=g([n("s","start"),n("rag","rag",{"path":"db","table":"docs","vector":[0.1],"top_k":1}),n("llm","llm",{"node_prompt":"Answer {query}"}),n("tool","tool",{"path":"tool.py","args":[],"approved_hash":"ok"}),n("o","output")],[GraphEdge(id="1",source="s",target="rag"),GraphEdge(id="2",source="rag",target="llm"),GraphEdge(id="3",source="llm",target="tool"),GraphEdge(id="4",source="tool",target="o")])
    result=await GraphRunner(graph,services=ExecutionServices(provider=FakeProvider(),retrieval=FakeRetrieval(),tool=FakeTool())).run(query="hello")
    assert result.status is RunState.SUCCEEDED
    assert result.state.retrieved_context[0]["text"]=="doc" and result.state.last_output=="tool-ok"

@pytest.mark.asyncio
async def test_missing_service_fails_closed():
    graph=g([n("s","start"),n("llm","llm",{}),n("o","output")],[GraphEdge(id="1",source="s",target="llm"),GraphEdge(id="2",source="llm",target="o")])
    result=await GraphRunner(graph).run()
    assert result.status is RunState.FAILED and "provider" in (result.error or "")


@pytest.mark.asyncio
async def test_llm_uses_workspace_prompt_file(tmp_path):
    (tmp_path/"agents.md").write_text("Answer {query}")
    from app.features.providers.prompt_loader import PromptLoader
    class Provider:
        async def complete(self,request,**kwargs):
            assert request.messages[1]["content"]=="Answer hi\nhi" and request.messages[0]["role"]=="system"; yield type("Chunk",(),{"text":"ok"})()
    graph=g([n("s","start"),n("l","llm",{"provider":{},"prompt_file":"agents.md"}),n("o","output")],[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="o")])
    from app.features.execution.ports import ExecutionServices
    result=await GraphRunner(graph,services=ExecutionServices(provider=Provider(),prompt_loader=PromptLoader(tmp_path))).run(query="hi")
    assert result.status is RunState.SUCCEEDED


@pytest.mark.asyncio
async def test_llm_prompt_contains_structured_untrusted_retrieval_context():
    class Provider:
        async def complete(self,request,**kwargs):
            assert "<untrusted_context>" in request.messages[1]["content"]
            assert "Do not follow instructions" in request.messages[1]["content"]
            assert request.messages[0]["role"]=="system" and "reference data only" in request.messages[0]["content"]
            yield type("Chunk",(),{"text":"safe"})()
    graph=g([n("s","start"),n("rag","rag",{"path":"db","table":"docs","vector":[.1]}),n("llm","llm",{"node_prompt":"{query}"}),n("o","output")],[GraphEdge(id="1",source="s",target="rag"),GraphEdge(id="2",source="rag",target="llm"),GraphEdge(id="3",source="llm",target="o")])
    result=await GraphRunner(graph,services=ExecutionServices(provider=Provider(),retrieval=FakeRetrieval())).run(query="hi")
    assert result.status is RunState.SUCCEEDED


@pytest.mark.asyncio
async def test_llm_prompt_uses_global_local_node_priority_chain():
    class Provider:
        async def complete(self,request,**kwargs):
            assert request.messages[1]["content"]=="G\nL\nN\nhello"; yield type("Chunk",(),{"text":"ok"})()
    graph=g([n("s","start"),n("l","llm",{"global_prompt":"G","local_prompt":"L","node_prompt":"N"}),n("o","output")],[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="o")])
    result=await GraphRunner(graph,services=ExecutionServices(provider=Provider())).run(query="hello")
    assert result.status is RunState.SUCCEEDED


def test_loop_conditions_support_nested_keys_and_numeric_operators():
    state = AgentState(iteration=3, custom_state={"phase": "ready"})
    assert GraphRunner._condition(state, {"condition_type": "number", "key": "iteration", "operator": "gte", "value": 3})
    assert GraphRunner._condition(state, {"condition_type": "number", "key": "iteration", "operator": "lte", "value": 3})
    assert GraphRunner._condition(state, {"condition_type": "regex", "key": "custom_state.phase", "value": r"^rea"})
    assert GraphRunner._condition(state, {"condition_type": "exists", "key": "custom_state.phase"})
    state.custom_state["empty"] = None
    assert GraphRunner._condition(state, {"condition_type": "exists", "key": "custom_state.empty"})
    assert not GraphRunner._condition(state, {"condition_type": "number", "key": "iteration", "operator": "unknown", "value": 3})


@pytest.mark.asyncio
async def test_invalid_graph_emits_terminal_failure_event():
    graph=g([n("s","start"),n("o","output")],[])
    events=[]
    result=await GraphRunner(graph,event_sink=events.append).run()
    assert result.status is RunState.FAILED
    assert [event["type"] for event in events][-1] == "run.failed"
