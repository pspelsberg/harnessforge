"""Public execution-state seam consumed by extension slices."""
from app.features.execution.state import AgentState, Reducer, StateLimitError, apply_reducer
__all__=["AgentState","Reducer","StateLimitError","apply_reducer"]
