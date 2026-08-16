import asyncio, json, subprocess, sys
from app.features.execution.engine import GraphRunner, RunState
from app.features.graph_authoring.contracts import ForgeGraph, GraphNode, GraphEdge
from app.features.export.generator import export_bundle

def n(i,t,c=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
def test_validated_reducer_graph_runs_and_exports(tmp_path):
    graph=ForgeGraph(id="g",name="e2e",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":False},nodes=[n("s","start"),n("r","reducer",{"op":"SET","target":"last_output","value":"done"}),n("o","output")],edges=[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")])
    result=asyncio.run(GraphRunner(graph).run(query="test")); assert result.status is RunState.SUCCEEDED
    bundle=tmp_path/"bundle"; export_bundle(graph,bundle); run=subprocess.run([sys.executable,str(bundle/"agent_runner.py"),"--prompt","test","--json-logs"],capture_output=True,text=True)
    assert run.returncode==0 and json.loads(run.stdout)["output"]=="done"


def test_service_built_tool_runs_in_local_trust_mode(tmp_path):
    import asyncio
    from app.features.execution.services import build_services
    (tmp_path/"tool.py").write_text("print('integration-ok')")
    graph=ForgeGraph(id="g",name="tool",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":False},nodes=[n("s","start"),n("t","tool",{"path":"tool.py","args":[]}),n("o","output")],edges=[GraphEdge(id="1",source="s",target="t"),GraphEdge(id="2",source="t",target="o")])
    from app.features.tool_execution.runner import ToolRunner,ToolSpec
    spec=ToolSpec(path="tool.py",args=[],timeout_seconds=15,allowed_write_dirs=[],env_allowlist=[]); approved=ToolRunner(tmp_path).config_hash(spec)
    tool_node=n("t","tool",{"path":"tool.py","args":[],"approved_hash":approved})
    graph=graph.model_copy(update={"nodes":[graph.nodes[0],tool_node,graph.nodes[2]]})
    services=build_services(graph,tmp_path)
    result=asyncio.run(GraphRunner(graph,services=services).run()); assert result.status is RunState.SUCCEEDED and result.state.last_output=="integration-ok\n"
