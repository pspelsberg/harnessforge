from pathlib import Path
import json
def test_forge_schema_artifact_is_versioned():
 p=Path(__file__).parents[3]/"docs/forge-schema-v1.json"; data=json.loads(p.read_text()); assert data["properties"]["schema_version"]["const"]=="1"
