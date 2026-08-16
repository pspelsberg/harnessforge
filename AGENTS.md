# HarnessForge contributor guide

- Backend: `cd backend && uv run pytest -q`; supported launcher is `python run.py` and binds to `127.0.0.1`.
- Frontend: `cd frontend && npm ci && npm test && npm run build`.
- Architecture: `backend/app/core` contains only shared primitives; use-case code belongs under `backend/app/features/<slice>`.
- Feature slices do not import private internals from other slices.
- Validate all workspace paths through `WorkspaceBoundary`; never use shell interpolation or `dangerouslySetInnerHTML`.
- External providers require fixed endpoint validation, environment-only secrets, and explicit dataflow approval.
- Tools are visibly Local Trust Mode, bounded, hash-approved subprocesses; do not claim OS sandboxing.
- Every security fix gets a deterministic regression test.
