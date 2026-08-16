import asyncio
import os
import pytest
from app.features.tool_execution.runner import ToolSpec, ToolRunner, ToolError

def test_tool_hash_changes_with_file_and_config(tmp_path):
    script=tmp_path/"tool.py"; script.write_text("print('ok')")
    spec=ToolSpec(path="tool.py", args=[], timeout_seconds=2, allowed_write_dirs=[])
    first=ToolRunner(tmp_path).config_hash(spec)
    script.write_text("print('changed')")
    assert first != ToolRunner(tmp_path).config_hash(spec)

def test_tool_requires_matching_approval(tmp_path):
    (tmp_path/"tool.py").write_text("print('ok')")
    runner=ToolRunner(tmp_path); spec=ToolSpec(path="tool.py", args=[], timeout_seconds=2, allowed_write_dirs=[])
    with pytest.raises(ToolError, match="approval"):
        asyncio.run(runner.run(spec, approved_hash="bad"))

def test_tool_captures_output_and_strips_secrets(tmp_path, monkeypatch):
    (tmp_path/"tool.py").write_text("import os; print(os.getenv('OPENAI_API_KEY', 'missing'))")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    runner=ToolRunner(tmp_path); spec=ToolSpec(path="tool.py", args=[], timeout_seconds=2, allowed_write_dirs=[])
    result=asyncio.run(runner.run(spec, approved_hash=runner.config_hash(spec)))
    assert result.returncode == 0 and result.trust_mode == "local_trust_mode" and "secret" not in result.stdout and result.stdout.strip() == "missing"

def test_tool_timeout_is_bounded(tmp_path):
    (tmp_path/"tool.py").write_text("import time; time.sleep(2)")
    runner=ToolRunner(tmp_path); spec=ToolSpec(path="tool.py", args=[], timeout_seconds=0.1, allowed_write_dirs=[])
    result=asyncio.run(runner.run(spec, approved_hash=runner.config_hash(spec)))
    assert result.timed_out


def test_tool_output_cap_terminates_without_buffering(tmp_path):
    (tmp_path/"tool.py").write_text("print('x' * 60000)")
    runner=ToolRunner(tmp_path); spec=ToolSpec(path="tool.py",args=[],timeout_seconds=2)
    with pytest.raises(ToolError, match="output"):
        asyncio.run(runner.run(spec, approved_hash=runner.config_hash(spec)))


def test_tool_spec_rejects_secret_environment_names(tmp_path):
    with pytest.raises(ValueError): ToolSpec(path="tool.py", args=[], env_allowlist=["OPENAI_API_KEY"])

def test_tool_spec_validates_write_directories(tmp_path):
    (tmp_path/"tool.py").write_text("print('ok')")
    runner=ToolRunner(tmp_path)
    with pytest.raises(ToolError):
        runner.config_hash(ToolSpec(path="tool.py", args=[], allowed_write_dirs=["../outside"]))


def test_tool_declared_write_directory_is_resolved_in_hash(tmp_path):
    (tmp_path/"tool.py").write_text("print('ok')"); (tmp_path/"out").mkdir()
    runner=ToolRunner(tmp_path); spec=ToolSpec(path="tool.py",args=[],allowed_write_dirs=["out"])
    assert runner.config_hash(spec) != runner.config_hash(ToolSpec(path="tool.py",args=[],allowed_write_dirs=[]))


def test_config_hash_includes_explicit_limits(tmp_path):
    (tmp_path/"tool.py").write_text("print('ok')"); runner=ToolRunner(tmp_path)
    assert runner.config_hash(ToolSpec(path="tool.py",args=[])) != runner.config_hash(ToolSpec(path="tool.py",args=[],timeout_seconds=15,allowed_write_dirs=[],env_allowlist=[]))


def test_tool_spec_bounds_environment_allowlist(tmp_path):
    with pytest.raises(ValueError): ToolSpec(path="tool.py",args=[],env_allowlist=["A"]*65)


def test_shell_and_javascript_tools_execute_as_scripts(tmp_path):
    (tmp_path/"tool.sh").write_text("printf shell-ok")
    (tmp_path/"tool.js").write_text("process.stdout.write('js-ok')")
    runner=ToolRunner(tmp_path)
    for name, expected in (("tool.sh","shell-ok"),("tool.js","js-ok")):
        spec=ToolSpec(path=name,args=[],timeout_seconds=2)
        result=asyncio.run(runner.run(spec,approved_hash=runner.config_hash(spec)))
        assert result.stdout==expected


def test_tool_hash_changes_when_file_timestamp_changes(tmp_path):
    import os,time
    script=tmp_path/"tool.py"; script.write_text("print('ok')"); runner=ToolRunner(tmp_path); spec=ToolSpec(path="tool.py",args=[])
    first=runner.config_hash(spec); now=time.time_ns()+10_000_000; os.utime(script,ns=(now,now))
    assert first != runner.config_hash(spec)
