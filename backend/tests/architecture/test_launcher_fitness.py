from pathlib import Path
def test_launcher_is_loopback_only():
 text=(Path(__file__).parents[2]/"run.py").read_text(); assert 'host="127.0.0.1"' in text and '0.0.0.0' not in text
