import pytest
from pydantic import ValidationError
from app.features.execution.state import AgentState, Reducer, ReducerOp, apply_reducer, StateLimitError

def test_reducer_mutates_only_declared_operations():
    state = AgentState(query="hello")
    apply_reducer(state, Reducer(op=ReducerOp.SET, target="last_output", value="ok"))
    assert state.last_output == "ok"
    apply_reducer(state, Reducer(op=ReducerOp.APPEND_LIST, target="messages", value={"role": "user", "content": "hi"}))
    assert state.messages[-1]["content"] == "hi"

def test_rejects_unknown_target_and_malformed_reducer():
    with pytest.raises(ValidationError): Reducer(op="EXEC", target="query", value="x")
    with pytest.raises(ValidationError): Reducer(op=ReducerOp.SET, target="__class__", value="x")

def test_state_size_cap_is_enforced():
    state = AgentState()
    with pytest.raises(StateLimitError): apply_reducer(state, Reducer(op=ReducerOp.SET, target="last_output", value="x" * (5 * 1024 * 1024)))


def test_failed_reducer_does_not_leave_oversized_mutation():
    state = AgentState()
    with pytest.raises(StateLimitError):
        apply_reducer(state, Reducer(op=ReducerOp.SET, target="last_output", value="x" * (5 * 1024 * 1024)))
    assert state.last_output is None


def test_agent_state_rejects_unknown_fields_and_non_json_values():
    with pytest.raises(ValidationError): AgentState(hacker="x")
    with pytest.raises(ValidationError): Reducer(op=ReducerOp.SET, target="query", value=object())


def test_agent_state_validates_nested_json_values_and_total_size():
    with pytest.raises(ValidationError):
        AgentState(metadata={"bad": object()})
    with pytest.raises(ValidationError):
        AgentState(last_output=float("inf"))
    with pytest.raises(ValidationError):
        AgentState(last_output="x" * (5 * 1024 * 1024))


def test_custom_state_reducer_uses_bounded_dotted_paths():
    state = AgentState(custom_state={"counter": 1, "items": []})
    apply_reducer(state, Reducer(op=ReducerOp.INCREMENT, target="custom_state.counter", value=2))
    apply_reducer(state, Reducer(op=ReducerOp.APPEND_LIST, target="custom_state.items", value="ok"))
    assert state.custom_state == {"counter": 3, "items": ["ok"]}
    with pytest.raises(ValidationError):
        Reducer(op=ReducerOp.SET, target="metadata.__class__", value="x")
