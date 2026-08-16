import asyncio, json
from app.features.execution.engine import GraphRunner,RunState
from app.features.execution.ports import ExecutionServices
from app.features.graph_authoring.contracts import ForgeGraph,GraphNode,GraphEdge
def n(i,t,c=None):return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
class Provider:
 async def complete(self,request,**kwargs): yield type("C",(),{"text":"model"})()
class Retrieval:
 def search(self,*args,**kwargs): return [{"text":"ref","score":.1,"metadata":{}}]
class Tool:
 async def run(self,spec,approved_hash): return type("R",(),{"stdout":"tool","stderr":"","returncode":0,"timed_out":False,"trust_mode":"local_trust_mode"})()
def test_complete_runtime_path(tmp_path):
 nodes=[n("s","start"),n("r","rag",{"path":"db","table":"docs","vector":[1]}),n("l","llm",{"node_prompt":"{query}"}),n("loop","loop",{"condition_type":"equals","key":"last_output","value":"model","max_iterations":1,"fallback":"f"}),n("tool","tool",{"path":"tool.py","args":[],"approved_hash":"x"}),n("f","reducer",{"op":"SET","target":"last_output","value":"fallback"}),n("o","output")]; edges=[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="l"),GraphEdge(id="3",source="l",target="loop"),GraphEdge(id="4",source="loop",target="tool",source_handle="true"),GraphEdge(id="5",source="tool",target="o"),GraphEdge(id="6",source="loop",target="f",source_handle="fallback"),GraphEdge(id="7",source="loop",target="f",source_handle="false"),GraphEdge(id="8",source="f",target="o")]; graph=ForgeGraph(id="g",name="complete",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":False},nodes=nodes,edges=edges); result=asyncio.run(GraphRunner(graph,services=ExecutionServices(provider=Provider(),retrieval=Retrieval(),tool=Tool())).run(query="q")); assert result.status is RunState.SUCCEEDED and result.state.last_output=="tool"
