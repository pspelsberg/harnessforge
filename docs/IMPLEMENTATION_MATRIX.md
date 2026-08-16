# Implementation matrix

| Slice | Implementation | Verification | Status |
|---|---|---|---|
| Foundation/schema/security | `backend/app/core`, graph contracts, path sanitizer, session | unit + architecture tests | verified |
| Graph authoring | graph API, workspace API, React Flow, custom nodes, inspector | backend/frontend tests | verified |
| Execution | AgentState, reducers, loops, async runner, pause/resume/cancel | unit/integration tests | verified |
| Providers | local OpenAI, Ollama, OpenRouter/OpenAI contracts, SSE, approval | fake-provider tests | verified with external network disabled |
| Retrieval | LanceDB inspector/query, untrusted context | real LanceDB integration | verified |
| Tools | Local Trust Mode, process groups, hash approval, limits | subprocess/security tests | verified; no OS sandbox claim |
| Observability | broker, WebSocket, events, SQLite, checkpoints, retention | API/store tests | verified |
| Export | validator, template, local provider/RAG/tool/loop runner, ZIP | isolated subprocess tests | verified for covered modes |
| Release | CI, launcher, API docs, security matrix, E2E | Pytest/Vitest/build | verified |

## Explicit non-claims

External provider network calls are not run in CI. Local Trust Mode is not an OS sandbox. Phase-2 features in ADR-007 are not implemented or activated.
