# Local API contract

All `/api/*` routes require `X-HarnessForge-Token`; requests are accepted only from configured localhost hosts/origins. The server binds to `127.0.0.1`.

- `GET /health`, `GET /ready` — local liveness/readiness.
- `POST /api/graph`, `GET /api/graph/{path}` — bounded `.forge.json` graph persistence.
- `POST /api/run` — validated active graph execution; returns `run_id`, status and bounded state.
- `POST /api/provider/approval` — returns a non-secret dataflow approval fingerprint.
- `POST /api/retrieval/query` — read-only bounded LanceDB query.
- `POST /api/export` — validates and creates runner files plus ZIP.
- `GET /api/runs`, `/api/runs/{id}/events`, `/api/runs/{id}/checkpoints` — bounded observability reads.
- `DELETE /api/runs/{id}`, `DELETE /api/runs` — explicit local deletion.
- `WS /ws` — token/origin-authenticated ping, run pause/resume/cancel and live events.

Secrets are never accepted in graph files or emitted events. External providers require explicit approval and environment-only keys.
