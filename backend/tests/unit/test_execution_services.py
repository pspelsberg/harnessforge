import pytest
from app.features.execution.services import build_services, ServiceBuildError
from app.features.graph_authoring.contracts import ForgeGraph, GraphNode

def n(i,t,c=None): return GraphNode(id=i,type=t,position={"x":0,"y":0},data={"config":c or {},"ui":{}})
def graph(nodes,review=False,external=False):
    if not any(x.type=="output" for x in nodes): nodes=[*nodes,n("o","output")]
    return ForgeGraph(id="g",name="g",workspace_path=".",settings={"review_only":review,"external_dataflow_activated":external},nodes=nodes,edges=[])

def test_builds_local_provider_and_tool_services(tmp_path):
    (tmp_path/"tool.py").write_text("print('ok')")
    g=graph([n("s","start"),n("llm","llm",{"provider":{"kind":"local_openai","base_url":"http://127.0.0.1:8000/v1","model":"local","timeout_seconds":2}}),n("tool","tool",{"path":"tool.py","args":[]})])
    from app.features.tool_execution.runner import ToolRunner,ToolSpec
    approved=ToolRunner(tmp_path).config_hash(ToolSpec(path="tool.py",args=[],timeout_seconds=15,allowed_write_dirs=[],env_allowlist=[]))
    data=g.model_dump(mode="json")
    for item in data["nodes"]:
        if item["id"]=="tool": item["data"]["config"]["approved_hash"]=approved
    g=ForgeGraph.model_validate(data)
    services=build_services(g,tmp_path)
    assert services.provider is not None and services.tool is not None

def test_external_provider_requires_graph_activation(tmp_path):
    g=graph([n("s","start"),n("llm","llm",{"provider":{"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2}})],external=False)
    with pytest.raises(ServiceBuildError,match="activation"): build_services(g,tmp_path)

def test_invalid_tool_path_fails_during_service_build(tmp_path):
    g=graph([n("s","start"),n("tool","tool",{"path":"../evil.py","args":[]})])
    with pytest.raises(ServiceBuildError): build_services(g,tmp_path)


def test_external_provider_requires_approval_fingerprint(tmp_path):
    g=graph([n("s","start"),n("llm","llm",{"provider":{"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2}}),n("o","output")],external=True)
    with pytest.raises(ServiceBuildError,match="approval"): build_services(g,tmp_path)


def test_external_provider_builds_with_valid_approval(tmp_path):
    from app.features.providers.adapters import DataflowApproval
    cfg={"kind":"openai","base_url":"https://api.openai.com/v1","model":"x","timeout_seconds":2}
    g=graph([n("s","start"),n("llm","llm",{"provider":cfg,"bindings":["query"]}),n("o","output")],external=True)
    config=__import__("app.features.providers.contracts",fromlist=["ProviderConfig"]).ProviderConfig.model_validate(cfg)
    approval=DataflowApproval.issue(config,["query"])
    g=g.model_copy(update={"nodes":[g.nodes[0],n("llm","llm",{"provider":cfg,"bindings":["query"],"approval_fingerprint":approval.fingerprint}),g.nodes[2]]})
    services=build_services(g,tmp_path); assert services.provider is not None and services.provider_approval is not None


def test_provider_bindings_must_be_bounded_strings(tmp_path):
    g=graph([n("s","start"),n("llm","llm",{"provider":{"kind":"local_openai","base_url":"http://127.0.0.1:8000/v1","model":"x","timeout_seconds":2},"bindings":["query",1]}),n("o","output")])
    with pytest.raises(ServiceBuildError): build_services(g,tmp_path)


def test_service_registry_preserves_multiple_node_bindings(tmp_path):
    graph_obj=graph([n("s","start"),n("l1","llm",{"provider":{"kind":"local_openai","base_url":"http://127.0.0.1:8000/v1","model":"a","timeout_seconds":2}}),n("l2","llm",{"provider":{"kind":"local_openai","base_url":"http://127.0.0.1:8000/v1","model":"b","timeout_seconds":2}}),n("o","output")])
    services=build_services(graph_obj,tmp_path)
    assert set(services.providers)=={"l1","l2"} and services.providers["l1"].config.model=="a" and services.providers["l2"].config.model=="b"
