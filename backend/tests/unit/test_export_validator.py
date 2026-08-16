import pytest
from app.features.export.validator import validate_export, ExportValidationError
from app.features.graph_authoring.contracts import ForgeGraph,GraphNode,GraphEdge

def n(i,t,c=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
def graph(tmp_path,nodes): return ForgeGraph(id="g",name="g",workspace_path=str(tmp_path),settings={"review_only":False,"external_dataflow_activated":False},nodes=nodes,edges=[GraphEdge(id="1",source="s",target="o")])
def test_validator_accepts_minimal_graph(tmp_path):
    assert validate_export(graph(tmp_path,[n("s","start"),n("o","output")]),tmp_path).errors==()
def test_validator_rejects_review_only_and_missing_tool_approval(tmp_path):
    g=graph(tmp_path,[n("s","start"),n("t","tool",{"path":"tool.py","args":[]}),n("o","output")]); g=ForgeGraph.model_validate({**g.model_dump(mode="json"),"settings":{"review_only":True,"external_dataflow_activated":False}})
    result=validate_export(g,tmp_path); assert any("review" in error for error in result.errors) and any("approval" in error for error in result.errors)
def test_validator_rejects_external_provider_without_activation(tmp_path):
    g=graph(tmp_path,[n("s","start"),n("l","llm",{"provider":{"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2}}),n("o","output")]); result=validate_export(g,tmp_path); assert any("activation" in error for error in result.errors)
def test_validator_rejects_missing_referenced_paths(tmp_path):
    g=graph(tmp_path,[n("s","start"),n("r","rag",{"path":"missing","table":"docs","vector":[1]}),n("o","output")]); result=validate_export(g,tmp_path); assert any("path" in error for error in result.errors)
