"""Public, versioned .forge.json graph contract."""
from __future__ import annotations

from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from math import isfinite


from app.core.json_values import validate_json_value
from app.core.config import CAPS


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and __import__("re").search(r"(?i)(api[_-]?key|secret|password|token|authorization)", key): return True
            if _contains_secret_key(item): return True
    elif isinstance(value, list): return any(_contains_secret_key(item) for item in value)
    return False

NodeType = Literal["start", "llm", "rag", "loop", "reducer", "tool", "output"]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class Position(StrictModel):
    x: float = Field(ge=-1_000_000, le=1_000_000, allow_inf_nan=False)
    y: float = Field(ge=-1_000_000, le=1_000_000, allow_inf_nan=False)

class NodeData(StrictModel):
    # Runtime configuration and UI metadata are intentionally separate surfaces.
    config: dict[str, Any] = Field(default_factory=dict)
    ui: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def validate_json_surfaces(cls, value: Any) -> Any:
        if not isinstance(value, dict) or set(value) - {"config", "ui"}:
            return value
        for key in ("config", "ui"):
            validate_json_value(value.get(key, {}))
            if key == "config" and _contains_secret_key(value.get(key, {})): raise ValueError("secret-shaped configuration is forbidden")
        return value

class GraphNode(StrictModel):
    id: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")]
    type: NodeType
    position: Position
    data: NodeData

class GraphEdge(StrictModel):
    id: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")]
    source: Annotated[str, Field(min_length=1, max_length=128)]
    target: Annotated[str, Field(min_length=1, max_length=128)]
    source_handle: Annotated[str | None, Field(default=None, max_length=64)] = None
    target_handle: Annotated[str | None, Field(default=None, max_length=64)] = None

class GraphSettings(StrictModel):
    review_only: bool = True
    external_dataflow_activated: bool = False
    debug_mode: bool = False
    retention_days: int = Field(default=30, ge=1, le=365)

class ForgeGraph(StrictModel):
    schema_version: Literal["1"] = "1"
    id: Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    workspace_path: Annotated[str, Field(min_length=1, max_length=4096)]
    nodes: list[GraphNode] = Field(min_length=2, max_length=CAPS.max_nodes)
    edges: list[GraphEdge] = Field(max_length=CAPS.max_edges)
    settings: GraphSettings = Field(default_factory=GraphSettings)

    @model_validator(mode="after")
    def validate_topology(self) -> "ForgeGraph":
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("node ids must be unique")
        if sum(node.type == "start" for node in self.nodes) != 1:
            raise ValueError("graph must contain exactly one start node")
        if sum(node.type == "output" for node in self.nodes) != 1:
            raise ValueError("graph must contain exactly one output node")
        edge_ids = [edge.id for edge in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("edge ids must be unique")
        known = set(node_ids)
        if any(edge.source not in known or edge.target not in known for edge in self.edges):
            raise ValueError("edge endpoints must reference existing nodes")
        if any(node.type == "output" and any(edge.source == node.id for edge in self.edges) for node in self.nodes):
            raise ValueError("output node must be terminal")
        node_types={node.id:node.type for node in self.nodes}
        allowed_handles={"true","false","fallback"}
        if any(edge.source_handle is not None and node_types.get(edge.source)=="loop" and edge.source_handle not in allowed_handles for edge in self.edges):
            raise ValueError("invalid loop edge handle")
        return self
