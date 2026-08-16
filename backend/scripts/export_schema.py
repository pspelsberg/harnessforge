from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from app.features.graph_authoring.contracts import ForgeGraph
Path(__file__).parents[2].joinpath("docs","forge-schema-v1.json").write_text(__import__("json").dumps(ForgeGraph.model_json_schema(),indent=2))
