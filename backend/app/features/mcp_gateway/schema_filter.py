"""Progressive disclosure and redaction for MCP schemas."""
from __future__ import annotations
from typing import Any
from app.core.extension_contracts import EXTENSION_POLICY
from app.core.security.redaction import redact_payload
from app.features.mcp_gateway.contracts import ToolDescriptor,ResourceDescriptor

class McpSchemaError(ValueError): pass

def filter_tool(tool: ToolDescriptor, *, full: bool=False) -> dict[str,Any]:
    schema=redact_payload(tool.input_schema)
    if not isinstance(schema,dict): raise McpSchemaError("invalid MCP schema")
    if full:
        return {"server_id":tool.server_id,"name":tool.name,"description":redact_payload(tool.description),"input_schema":schema}
    properties=schema.get("properties",{}) if isinstance(schema.get("properties",{}),dict) else {}
    required=schema.get("required",[]) if isinstance(schema.get("required",[]),list) else []
    summary={"type":schema.get("type","object"),"properties":{str(k):{"type":v.get("type","string")} for k,v in list(properties.items())[:16] if isinstance(v,dict)},"required":[str(x) for x in required[:16]]}
    return {"server_id":tool.server_id,"name":tool.name,"description":str(redact_payload(tool.description))[:512],"input_schema":summary}

def filter_resource(resource: ResourceDescriptor)->dict[str,str]:
    return {"server_id":resource.server_id,"uri":resource.uri,"name":resource.name,"description":str(redact_payload(resource.description))[:512]}


def validate_arguments(tool: ToolDescriptor, arguments: dict[str,Any]) -> None:
    schema=tool.input_schema
    properties=schema.get("properties",{}) if isinstance(schema.get("properties",{}),dict) else {}
    required=schema.get("required",[]) if isinstance(schema.get("required",[]),list) else []
    if any(name not in arguments for name in required if isinstance(name,str)): raise McpSchemaError("required MCP argument missing")
    if schema.get("additionalProperties") is False and any(name not in properties for name in arguments): raise McpSchemaError("unknown MCP argument")
    for name,value in arguments.items():
        rule=properties.get(name)
        if not isinstance(rule,dict): continue
        expected=rule.get("type")
        valid={"string":isinstance(value,str),"integer":isinstance(value,int) and not isinstance(value,bool),"number":isinstance(value,(int,float)) and not isinstance(value,bool),"boolean":isinstance(value,bool),"object":isinstance(value,dict),"array":isinstance(value,list)}.get(expected,True)
        if not valid: raise McpSchemaError("MCP argument type is invalid")
