from pathlib import Path
def test_api_docs_exist_and_forbid_secret_claims():
 text=(Path(__file__).parents[3]/"docs/API.md").resolve().read_text().lower(); assert "x-harnessforge-token" in text and "never accepted" in text
