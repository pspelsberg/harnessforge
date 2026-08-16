import asyncio, json, subprocess, sys
from app.features.execution.engine import GraphRunner,RunState
from app.features.execution.ports import ExecutionServices
from app.features.graph_authoring.contracts import ForgeGraph,GraphNode,GraphEdge
from app.features.export.generator import export_bundle,package_zip
def node(i,t,c=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
class R: 
 def search(self,*args,**kwargs): return [{"text":"reference","score":.1,"metadata":{}}]
class P:
 async def complete(self,request,**kwargs): yield type("C",(),{"text":"answer"})()
class T:
 async def run(self,spec,approved_hash): return type("R",(),{"stdout":"tool-output","stderr":"","returncode":0})()
async def run_flow(graph): return await GraphRunner(graph,services=ExecutionServices(provider=P(),retrieval=R(),tool=T())).run(query="release")
def test_release_flow_fake_external_boundaries(tmp_path):
 graph=ForgeGraph(id="release",name="release",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":True},nodes=[node("s","start"),node("rag","rag",{"path":"db","table":"docs","vector":[.1]}),node("llm","llm",{"node_prompt":"{query}"}),node("tool","tool",{"path":"tool.py","args":[],"approved_hash":"ok"}),node("o","output")],edges=[GraphEdge(id="1",source="s",target="rag"),GraphEdge(id="2",source="rag",target="llm"),GraphEdge(id="3",source="llm",target="tool"),GraphEdge(id="4",source="tool",target="o")])
 result=asyncio.run(run_flow(graph)); assert result.status is RunState.SUCCEEDED and result.state.last_output=="tool-output"
 bundle=tmp_path/"bundle"; files=export_bundle(ForgeGraph(id="simple",name="simple",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":False},nodes=[node("s","start"),node("r","reducer",{"op":"SET","target":"last_output","value":"ok"}),node("o","output")],edges=[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")]),bundle); archive=package_zip(files,tmp_path/"bundle.zip"); run=subprocess.run([sys.executable,str(bundle/"agent_runner.py"),"--prompt","release","--json-logs"],capture_output=True,text=True); assert run.returncode==0 and json.loads(run.stdout)["output"]=="ok" and archive.exists()
