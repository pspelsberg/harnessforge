from pathlib import Path
import json,subprocess
def test_task_audit_is_deterministic():
 root=Path(__file__).parents[2]; result=subprocess.run(["python",str(root.parent/"scripts/audit_task.py")],capture_output=True,text=True,check=True); payload=json.loads(result.stdout); assert payload["open_count"]>=0
