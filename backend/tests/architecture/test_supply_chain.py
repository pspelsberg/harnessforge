from pathlib import Path
import tomllib
def test_backend_dependencies_are_exactly_pinned():
 data=tomllib.loads((Path(__file__).parents[2]/"pyproject.toml").read_text())
 assert all(("==" in dep) for dep in data["project"]["dependencies"])
def test_export_source_has_no_backend_framework_imports():
 source=(Path(__file__).parents[2]/"app/features/export/generator.py").read_text().lower(); assert "fastapi" not in source and "react" not in source


def test_uv_lock_is_present_and_nonempty():
    lock=Path(__file__).parents[2]/"uv.lock"; assert lock.is_file() and lock.stat().st_size>1000


def test_release_audit_and_api_docs_exist():
 root=Path(__file__).parents[3]; assert (root/"docs/RELEASE_AUDIT.md").is_file() and (root/"docs/API.md").is_file() and (root/"AGENTS.md").is_file()
