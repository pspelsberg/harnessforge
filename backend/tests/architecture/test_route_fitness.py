from pathlib import Path
def test_composition_root_contains_protected_core_routes():
 text=(Path(__file__).parents[2]/"app/main.py").read_text(); assert "/api/run" in text and "/api/export" in text and "/ws" in text and "Depends(auth)" in text
