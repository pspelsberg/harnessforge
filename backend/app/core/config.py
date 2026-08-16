"""Immutable security/resource limits shared by slices."""
from dataclasses import dataclass

@dataclass(frozen=True)
class HardCaps:
    max_nodes: int = 50
    max_edges: int = 200
    max_state_bytes: int = 5 * 1024 * 1024
    max_run_seconds: float = 300.0
    max_loop_iterations: int = 50
    max_tool_timeout_seconds: float = 60.0
    max_output_bytes: int = 50 * 1024
    max_event_bytes: int = 256 * 1024
    max_request_bytes: int = 2 * 1024 * 1024
    max_auth_failures: int = 20

CAPS = HardCaps()
