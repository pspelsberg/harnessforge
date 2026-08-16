from pathlib import Path
import json,re
root=Path(__file__).parents[1]; task=(root/"task.md").read_text().splitlines(); source="\n".join(p.read_text(errors="ignore") for p in (root/"backend/app").rglob("*.py"))
items=[]
for line_no,line in enumerate(task,1):
 if "- [ ]" not in line: continue
 lower=line.lower(); evidence=[]
 for token in ["pytest","vitest","lancedb","websocket","export","workspace","provider","reducer","loop","tool","prompt","retention"]:
  if token in lower and token in source.lower(): evidence.append(token)
 items.append({"line":line_no,"task":line.strip(),"evidence_tokens":evidence,"status":"open"})
print(json.dumps({"open_count":len(items),"items":items},ensure_ascii=False,indent=2))
