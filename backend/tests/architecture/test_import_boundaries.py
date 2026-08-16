from pathlib import Path
import ast


def imports(path: Path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_core_does_not_import_features():
    root = Path(__file__).parents[2] / "app" / "core"
    violations = [(p, name) for p in root.rglob("*.py") for name in imports(p) if name.startswith("app.features")]
    assert violations == []


def test_features_do_not_import_private_modules_of_other_features():
    root = Path(__file__).parents[2] / "app" / "features"
    violations = []
    for path in root.rglob("*.py"):
        for name in imports(path):
            if name.startswith("app.features."):
                parts = name.split(".")
                if len(parts) >= 4 and parts[3].startswith("_"):
                    violations.append((path, name))
    assert violations == []


def test_no_cross_feature_private_imports():
    root=Path(__file__).parents[2]/"app/features"; violations=[]
    for path in root.rglob("*.py"):
        for name in imports(path):
            parts=name.split(".")
            if len(parts)>=4 and parts[0:2]==["app","features"] and parts[3].startswith("_"): violations.append((str(path),name))
    assert violations==[]
