# ADR-007: Architektonische Abgrenzung der Phase-2-Funktionen

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

Folgende Funktionen sind ausdrücklich Phase 2 und werden im MVP weder aktiviert noch durch implizite Fallbacks vorweggenommen:

- Human-Gate / HITL
- Sub-Graphs
- MCP-Autodiscovery und MCP-Governance-Gateway
- Guardrail-Node
- Time-Travel-Debugging
- RLM-/REPL-Codeausführung und Isolation
- stärkere Docker/Podman/WASM-Sandbox

`docs/PLAN.md` dokumentiert diese Grenzen und verlangt für jede spätere Einführung neue Verträge, Berechtigungen, Auditierung und Security-Regressionen.

## Begründung

Diese Funktionen erhöhen Privilegien, Kontextkomplexität, Persistenzumfang und Angriffsfläche erheblich. Ein MVP ohne sie bleibt statisch validierbar, lokal kontrollierbar und exportierbar.

## Sicherheitsbedingungen für spätere Einführung

- MCP nur mit versionierten Schemas, Progressive Disclosure, Governance-/Audit-Gateway und untrusted-resource-Markierung.
- Sub-Graphs nur mit explizitem Port-Mapping und Context Firewall.
- RLM/REPL nur in echter Code-Sandbox mit Rekursions-, CPU-, Speicher- und Output-Limits; kein direktes Ausführen von LLM-Code im Hostprozess.
- Time-Travel nur mit Integritäts-, Datenschutz-, Retention- und Edit-Replay-Vertrag.
- Human-Gates mit klarer Run-Identität, Ablauf, Audit-Log und sicherem Default.
- Guardrails dürfen nicht als vollständiger Prompt-Injection-Schutz beworben werden.
