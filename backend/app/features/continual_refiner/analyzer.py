"""Deterministic trajectory facts; untrusted text is never executed."""
from __future__ import annotations
from app.features.continual_refiner.contracts import Trajectory,Finding
class Analyzer:
 def analyze(self,trajectory:Trajectory)->list[Finding]:
  failed=sum(1 for event in trajectory.events if str(event.get("type","")).casefold() in {"failed","error"})
  if not failed: return []
  return [Finding(finding_id=f"finding-{trajectory.run_id}-failures",kind="fact",title="Run enthält fehlgeschlagene Schritte",evidence=[f"deterministisch gezählte Fehler: {failed}"],risk="medium",confidence=1.0)]
