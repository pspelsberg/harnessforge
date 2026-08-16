import pytest
from app.core.security.path_sanitizer import WorkspaceBoundary
from app.features.tool_execution.policy import validate_write_target
from app.features.tool_execution.runner import ToolError
def test_write_policy_requires_declared_directory(tmp_path):
    (tmp_path/"out").mkdir(); boundary=WorkspaceBoundary(tmp_path)
    assert validate_write_target(boundary,"out/file.txt",["out"]).name=="file.txt"
    with pytest.raises(ToolError): validate_write_target(boundary,"file.txt",["out"])


def test_write_policy_rejects_invalid_declared_directory(tmp_path):
    boundary=WorkspaceBoundary(tmp_path)
    with pytest.raises(ToolError): validate_write_target(boundary,"file.txt",["../outside"])
