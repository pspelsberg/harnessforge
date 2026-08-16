from typing import Annotated
from pydantic import BaseModel,ConfigDict,Field
class RetrievalRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    path: str=Field(min_length=1,max_length=4096)
    table: str=Field(min_length=1,max_length=128)
    vector: list[float]=Field(min_length=1,max_length=4096)
    top_k: Annotated[int,Field(ge=1,le=20)]=5
    text_query: str | None = Field(default=None, max_length=131072)
    hybrid: bool = False
