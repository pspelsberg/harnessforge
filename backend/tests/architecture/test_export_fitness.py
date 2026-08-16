from pathlib import Path

def test_generated_runner_template_has_no_backend_framework_imports():
    source=(Path(__file__).parents[2]/"app/features/export/generator.py").read_text().lower()
    assert "fastapi" not in source and "react" not in source

def test_core_has_no_feature_imports():
    root=Path(__file__).parents[2]/"app/core"
    assert all("app.features" not in p.read_text() for p in root.rglob("*.py"))


def test_standalone_template_is_versioned():
    template=Path(__file__).parents[3]/"templates"/"standalone_runner.py.jinja"
    assert template.is_file() and "validate_startup" in template.read_text()


def test_export_template_has_no_forbidden_framework_names():
 template=(Path(__file__).parents[3]/"templates/standalone_runner.py.jinja").read_text().lower(); assert "fastapi" not in template and "react" not in template and "harnessforge" not in template
