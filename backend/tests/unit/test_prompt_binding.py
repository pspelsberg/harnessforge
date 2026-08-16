import pytest
from app.features.providers.prompt_binding import compose_prompt, interpolate_prompt, PromptBindingError

def test_prompt_priority_and_bounded_variables():
    result=compose_prompt(global_prompt="global",local_prompt="local",node_prompt="node",state={"query":"hello","last_output":"done"})
    assert result == "global\nlocal\nnode\nhello\ndone"

def test_interpolation_rejects_unknown_or_code_expressions():
    with pytest.raises(PromptBindingError): interpolate_prompt("{unknown}",{})
    with pytest.raises(PromptBindingError): interpolate_prompt("{{ config.__class__ }}",{})

def test_prompt_length_is_bounded():
    with pytest.raises(PromptBindingError): compose_prompt(global_prompt="x"*200000,local_prompt="",node_prompt="",state={})
