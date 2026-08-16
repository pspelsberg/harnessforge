# ADR-008: MVP release gates and non-claims

- **Status:** Accepted
- **Context:** HarnessForge MVP release audit

The MVP release gate accepts deterministic local tests, fake-provider integration, real local LanceDB tests, bounded export runner tests and localhost API/WS tests. CI does not call external OpenAI/OpenRouter services. External network behavior is protected by allowlists and approval but requires an operator-owned staging test.

Local Trust Mode is intentionally not an OS sandbox. Write policy is declarative/preflight; untrusted tools require an external OS sandbox. Full production parity for every provider/RAG/async streaming option is a post-MVP gate.

Phase-2 functions listed in ADR-007 remain disabled. No release claim may imply they are available.
