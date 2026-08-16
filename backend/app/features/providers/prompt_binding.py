"""Safe prompt composition without templates or code evaluation."""
from __future__ import annotations
from typing import Any
from app.core.config import CAPS
class PromptBindingError(ValueError): pass
_ALLOWED={"query","retrieved_context","last_output","iteration"}
def interpolate_prompt(template:str, state:dict[str,Any])->str:
    if not isinstance(template,str) or len(template.encode()) > 128*1024: raise PromptBindingError("prompt is too large")
    output=[]; index=0
    while index < len(template):
        start=template.find("{",index)
        if start < 0: output.append(template[index:]); break
        output.append(template[index:start])
        end=template.find("}",start+1)
        if end < 0: raise PromptBindingError("unclosed prompt variable")
        key=template[start+1:end]
        if key not in _ALLOWED: raise PromptBindingError("unknown prompt variable")
        value=state.get(key,"")
        if isinstance(value,(dict,list)): value=str(value)
        elif value is None: value=""
        elif not isinstance(value,(str,int,float)): raise PromptBindingError("invalid prompt value")
        output.append(str(value)); index=end+1
    result="".join(output)
    if len(result.encode()) > 128*1024: raise PromptBindingError("prompt is too large")
    return result
def compose_prompt(*,global_prompt:str,local_prompt:str,node_prompt:str,state:dict[str,Any])->str:
    parts=[interpolate_prompt(value,state) for value in (global_prompt,local_prompt,node_prompt)]
    dynamic="\n".join(interpolate_prompt("{" + key + "}",state) for key in ("query","retrieved_context","last_output") if key in state and state.get(key) not in (None,"",[],{},()))
    result="\n".join(part for part in parts+[dynamic] if part)
    if len(result.encode()) > 128*1024: raise PromptBindingError("prompt is too large")
    return result
