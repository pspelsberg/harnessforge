from pathlib import Path
import re
def test_no_telemetry_or_tracking_imports():
 text="\n".join(p.read_text(errors="ignore").lower() for p in (Path(__file__).parents[2]/"app").rglob("*.py")); assert not re.search(r"(?:sentry_sdk|posthog|import\s+segment)",text)
