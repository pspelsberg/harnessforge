from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.features.graph_authoring.contracts import ForgeGraph
class RunRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    graph: ForgeGraph
    query: str=Field(default="",max_length=131072)
    @field_validator("query")
    @classmethod
    def safe_query(cls,value):
        if "\x00" in value: raise ValueError("query contains forbidden character")
        return value
