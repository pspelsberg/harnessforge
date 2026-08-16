# Phase-2 Threat Model

## Trust boundaries

The browser, provider responses, MCP responses, tool output, trajectory text, index snippets and harness template descriptions are untrusted. The local workspace is trusted only through `WorkspaceBoundary`; subprocesses remain Local Trust Mode and are not claimed to be OS sandboxed.

## Invariants

1. Extensions are opt-in and default-deny.
2. Secrets are environment-only and redacted before persistence or display.
3. Paths, graph hashes, run/session identities and action fingerprints are bound at public seams.
4. SQLite transitions are parameterized and atomic; approvals and refiner mutations are single-use/CAS-controlled.
5. Forks never inherit approvals; external fork actions are simulated or require fresh approval.
6. Index retrieval is read-only and labelled untrusted context; harnesses never construct shell commands or publish artifacts.
7. User-visible previews are text, not HTML, and all hard caps are deterministic.

Mitigations are backed by backend security regressions and focused Vitest suites for XSS, prompt injection, replay/expiry, TOCTOU, traversal, symlinks, binary/large files, infinite repair loops and unsafe Git actions.
