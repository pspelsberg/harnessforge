from pydantic import BaseModel,ConfigDict,Field
from app.features.graph_authoring.contracts import ForgeGraph
class ExportRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    graph: ForgeGraph
    destination: str=Field(min_length=1,max_length=4096)
