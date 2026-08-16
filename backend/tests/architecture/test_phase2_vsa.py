"""Ratchet: Phase-2 slices may consume only public cross-slice seams."""
import ast
from pathlib import Path
ROOT=Path(__file__).parents[2]
SLICES={"repl_sandbox","rlm","mcp_gateway","human_gates","time_travel","continual_refiner","workspace_indexer","coding_harness"}
ALLOWED={"contracts","events","public","ports","api_models"}
def test_phase2_cross_slice_imports_use_public_modules():
 violations=[]
 for feature in SLICES:
  for path in (ROOT/"app"/"features"/feature).glob("*.py"):
   tree=ast.parse(path.read_text(),filename=str(path))
   for node in ast.walk(tree):
    if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith("app.features."):
     parts=node.module.split("."); other=parts[2] if len(parts)>2 else ""; module=parts[3] if len(parts)>3 else ""
     if other!=feature and module not in ALLOWED: violations.append(f"{path}: {node.module}")
 assert not violations, "private cross-slice imports: "+"; ".join(violations)
