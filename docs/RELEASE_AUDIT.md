# MVP Release Audit

## Evidence (latest run)

- Backend: 235+ Pytest tests pass (including complete runtime-path and release smoke tests).
- Frontend: 32 Vitest tests pass; TypeScript/Vite build passes.
- Backend compileall and CI commands are defined.
- Localhost API, WebSocket, graph, run, retrieval, observability, export and ZIP smoke tests pass.
- Real local LanceDB inspector/query integration passes.
- Local OpenAI-compatible and Ollama protocol export tests pass.
- Complete fake-provider RAG → LLM → Loop → Tool → Output runtime path passes.
- Tool approval, workspace boundary, SSRF, secret redaction, untrusted-context and DoS regression tests pass.

## Open gates

- No live external network provider is exercised in CI by design; external OpenAI/OpenRouter operation remains approval-/environment-gated.
- Local Trust Mode intentionally does not claim OS-level sandboxing; declarative write-policy preflight is implemented.
- Standalone runner parity is covered for local HTTP, Ollama, LanceDB, loops, tools and reducers, but not every backend option.
- Full task-board checkbox completion requires an explicit product decision for deferred production features and is not inferred from test count.

See ADR-008 for the accepted local release gate and explicit non-claims.


## Phase-2 Release Audit

Die Phase-2-Slices bleiben opt-in und verändern das MVP nicht implizit. Sicherheitsnachweise umfassen deterministische Regressionen für SSRF/Workspace-Pfade, Prompt-Injection, Redaction, Binary-/Large-File-DoS, Approval Replay/Expiry/TOCTOU, Fork State Poisoning, Refiner Patch-/Rollback-Races, Harness Infinite Repair Loops und Git Push Gates. Supply-Chain-Grundlage: exakte Backend-Versionen, reproduzierbarer Frontend-Lockfile-Build und lokale, hashvalidierte Harness-Templates.

Rollback: Phase-2-Routen können deaktiviert werden; MVP-Graph-, Execution-, Export- und Provider-Pfade bleiben ohne Phase-2-Aktivierung funktionsfähig.
