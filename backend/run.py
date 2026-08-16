"""Security-preserving backend launcher; never binds beyond loopback."""
import uvicorn
from app.main import app

if __name__ == "__main__":
    token = getattr(app.state, "session_token", None)
    token_str = token.value if token else "none"
    print(f"\n=======================================================")
    print(f"⚡ HarnessForge Backend running at http://127.0.0.1:8000")
    print(f"🔑 Session Token: {token_str}")
    print(f"=======================================================\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
