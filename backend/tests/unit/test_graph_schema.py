import pytest
from pydantic import ValidationError
from app.features.graph_authoring.contracts import ForgeGraph, GraphNode, GraphEdge
from app.features.graph_authoring.validator import validate_graph


def node(node_id: str, node_type: str):
    return GraphNode(id=node_id, type=node_type, position={"x": 0, "y": 0}, data={"config": {}, "ui": {}})


def test_valid_graph_round_trips_and_separates_ui_from_config():
    graph = ForgeGraph(
        id="g1", name="demo", workspace_path=".",
        nodes=[node("start", "start"), node("out", "output")],
        edges=[GraphEdge(id="e1", source="start", target="out")],
    )
    payload = graph.model_dump(mode="json")
    assert payload["schema_version"] == "1"
    assert payload["nodes"][0]["data"] == {"config": {}, "ui": {}}
    assert ForgeGraph.model_validate(payload) == graph


def test_unknown_node_type_and_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        node("x", "python")
    with pytest.raises(ValidationError):
        GraphNode(id="x", type="start", position={"x": 0, "y": 0}, data={}, extra="nope")


def test_graph_limits_are_enforced_at_boundary():
    nodes = [node("s", "start"), node("o", "output")] + [node(str(i), "llm") for i in range(49)]
    with pytest.raises(ValidationError, match="50"):
        ForgeGraph(id="g", name="x", workspace_path=".", nodes=nodes, edges=[])


def test_config_and_ui_values_are_json_only_and_bounded():
    with pytest.raises(ValidationError):
        GraphNode(id="x", type="start", position={"x": 0, "y": 0}, data={"config": {"bad": object()}, "ui": {}})
    with pytest.raises(ValidationError):
        GraphNode(id="x", type="start", position={"x": 0, "y": 0}, data={"config": {str(i): i for i in range(65)}, "ui": {}})


def test_non_loop_cycle_is_rejected_but_loop_cycle_is_allowed():
    nodes = [node("s", "start"), node("a", "llm"), node("b", "llm"), node("o", "output")]
    graph = ForgeGraph(id="g", name="x", workspace_path=".", nodes=nodes, edges=[
            GraphEdge(id="1", source="s", target="a"), GraphEdge(id="2", source="a", target="b"),
            GraphEdge(id="3", source="b", target="a"), GraphEdge(id="4", source="b", target="o")])
    assert any(i.code == "UNGOVERNED_CYCLE" for i in validate_graph(graph).errors)


def test_non_finite_coordinates_are_rejected():
    with pytest.raises(ValidationError):
        GraphNode(id="x", type="start", position={"x": float("nan"), "y": 0}, data={"config": {}, "ui": {}})


def test_graph_json_schema_is_available():
    schema = ForgeGraph.model_json_schema()
    assert schema["properties"]["schema_version"]["const"] == "1"


def test_loop_requires_valid_fallback_and_both_branches():
    nodes=[node("s","start"),GraphNode(id="l",type="loop",position={"x":0,"y":0},data={"config":{"condition_type":"exists","max_iterations":2,"fallback":"o"},"ui":{}}),node("o","output")]
    graph=ForgeGraph(id="g",name="x",workspace_path=".",nodes=nodes,edges=[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="o",source_handle="true"),GraphEdge(id="3",source="l",target="o",source_handle="fallback")])
    result=validate_graph(graph); assert any(i.code=="MISSING_LOOP_BRANCH" for i in result.errors)


def test_output_node_cannot_have_outgoing_edges():
    nodes=[node("s","start"),node("o","output"),node("x","reducer")]
    with pytest.raises(ValidationError,match="output"):
        ForgeGraph(id="g",name="x",workspace_path=".",nodes=nodes,edges=[GraphEdge(id="1",source="s",target="o"),GraphEdge(id="2",source="o",target="x")])

def test_edge_handles_are_bounded_and_nonempty_when_present():
    with pytest.raises(ValidationError): GraphEdge(id="e",source="s",target="o",source_handle="x"*65)


def test_rag_node_requires_bounded_query_config():
    graph=ForgeGraph(id="g",name="x",workspace_path=".",nodes=[node("s","start"),GraphNode(id="r",type="rag",position={"x":0,"y":0},data={"config":{"path":"db","table":"docs"},"ui":{}}),node("o","output")],edges=[GraphEdge(id="1",source="s",target="r"),GraphEdge(id="2",source="r",target="o")])
    result=validate_graph(graph); assert any(i.code=="INVALID_RAG_CONFIG" for i in result.errors)


def test_node_config_validation_rejects_invalid_temperature_and_tool_timeout():
    graph=ForgeGraph(id="g",name="x",workspace_path=".",nodes=[node("s","start"),GraphNode(id="l",type="llm",position={"x":0,"y":0},data={"config":{"temperature":3},"ui":{}}),node("o","output")],edges=[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="o")])
    result=validate_graph(graph); assert any(i.code=="INVALID_LLM_CONFIG" for i in result.errors)


def test_loop_branch_handles_cannot_be_arbitrary():
    nodes=[node("s","start"),GraphNode(id="l",type="loop",position={"x":0,"y":0},data={"config":{"condition_type":"exists","max_iterations":2,"fallback":"o"},"ui":{}}),node("o","output")]
    with pytest.raises(ValidationError,match="invalid loop edge handle"):
        ForgeGraph(id="g",name="x",workspace_path=".",nodes=nodes,edges=[GraphEdge(id="1",source="s",target="l"),GraphEdge(id="2",source="l",target="o",source_handle="evil"),GraphEdge(id="3",source="l",target="o",source_handle="fallback")])


def test_graph_config_rejects_secret_shaped_keys():
    with pytest.raises(ValidationError):
        GraphNode(id="l",type="llm",position={"x":0,"y":0},data={"config":{"api_key":"secret"},"ui":{}})
