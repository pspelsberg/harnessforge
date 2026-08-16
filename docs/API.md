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


## Phase-2-Controller

Alle folgenden Routen sind am Composition Root authentifiziert und verwenden `contract_version: "1"`: `/api/gates`, `/api/time-travel/*`, `/api/refiner/*`, `/api/index/*` und `/api/harness/*`.

- Human-Gates: Request → Decision → single-use Consume; TTL, Nonce, Session, Run, Graph und Workspace werden gebunden.
- Time-Travel: Checkpoint-Lesen und Fork mit validierten Reducern; alte Approvals werden nicht kopiert.
- Refiner: Analyse liefert nur redigierte Vorschläge; Apply benötigt eine exakt gebundene Gate-Consume-Anfrage; Rollback ist hash- und CAS-geschützt.
- Indexer: Rebuild ist versioniert/atomar, Retrieval ist read-only und als `untrusted_workspace_context` markiert.
- Coding-Harness: Templates sind hashvalidiert; Plans führen keine Shell-Kommandos aus, Push ist opt-in und immer Gate-pflichtig.
- RLM/REPL: Beide APIs/UI-Flows bleiben standardmäßig deaktiviert; RLM nutzt ohne injizierten Provider einen fail-closed Disabled-Port, der Local-Trust-REPL bleibt explizit gekennzeichnet.
- Tool-/MCP-/RLM-Aktionen können über öffentliche Approval-Ports als Human-Gate-pflichtig deklariert werden; Parameterbindungen enthalten die konkrete Konfiguration bzw. Argumente.
