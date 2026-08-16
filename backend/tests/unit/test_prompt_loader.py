import pytest
from app.features.providers.prompt_loader import PromptLoader, PromptLoadError

def test_loader_reads_agents_markdown_only_with_limits(tmp_path):
    (tmp_path/"agents.md").write_text("Be concise.",encoding="utf-8")
    loader=PromptLoader(tmp_path)
    assert loader.load("agents.md")=="Be concise."

def test_loader_rejects_traversal_non_utf8_and_oversized(tmp_path):
    loader=PromptLoader(tmp_path)
    with pytest.raises(PromptLoadError): loader.load("../agents.md")
    (tmp_path/"bad.md").write_bytes(b"\xff")
    with pytest.raises(PromptLoadError): loader.load("bad.md")
    (tmp_path/"large.md").write_text("x"*(128*1024+1))
    with pytest.raises(PromptLoadError): loader.load("large.md")

def test_loader_hot_reload_hash_changes(tmp_path):
    (tmp_path/"agents.md").write_text("one")
    loader=PromptLoader(tmp_path); first=loader.fingerprint("agents.md")
    (tmp_path/"agents.md").write_text("two")
    assert loader.fingerprint("agents.md") != first
