# HarnessForge Backend

## Development

```bash
uv sync
uv run pytest -q
python run.py
```

The supported launcher binds only to `127.0.0.1:8000`. The API session token is generated per process; protected routes require `X-HarnessForge-Token`.

Current slices: graph contracts/validation, bounded execution, provider security/adapters, retrieval normalization, Local Trust Mode tools, observability persistence, export bundles, and FastAPI bootstrap.

## Release verification

Run `make release-check` for backend Pytest, frontend Vitest and the production build. The integration suite includes a localhost API/run/event/export smoke flow.
