import os
import pytest
from app.core.security.path_sanitizer import PathPolicy, WorkspaceBoundary, UnsafePathError


def test_allows_existing_workspace_file(tmp_path):
    (tmp_path / "notes.md").write_text("hello")
    result = WorkspaceBoundary(tmp_path).resolve("notes.md", must_exist=True)
    assert result == (tmp_path / "notes.md").resolve()


@pytest.mark.parametrize("candidate", ["../outside", ".env", ".ssh/key", "a\x00b", "/etc/passwd"])
def test_rejects_unsafe_paths(tmp_path, candidate):
    with pytest.raises(UnsafePathError):
        WorkspaceBoundary(tmp_path).resolve(candidate)


def test_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside-secret"
    outside.write_text("secret")
    link = tmp_path / "link"
    link.symlink_to(outside)
    with pytest.raises(UnsafePathError):
        WorkspaceBoundary(tmp_path).resolve("link", must_exist=True)


def test_policy_rejects_sensitive_names(tmp_path):
    policy = PathPolicy(sensitive_names=frozenset({".env", ".git"}))
    with pytest.raises(UnsafePathError):
        WorkspaceBoundary(tmp_path, policy=policy).resolve(".git/config")


def test_symlink_to_sensitive_file_is_rejected(tmp_path):
    secret = tmp_path / ".env"
    secret.write_text("KEY=secret")
    link = tmp_path / "notes.md"
    link.symlink_to(secret)
    with pytest.raises(UnsafePathError):
        WorkspaceBoundary(tmp_path).resolve("notes.md", must_exist=True)


def test_system_directory_cannot_be_selected_as_workspace(tmp_path):
    from pathlib import Path
    if Path("/etc").exists():
        with pytest.raises(UnsafePathError): WorkspaceBoundary("/etc")
