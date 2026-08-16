# ADR-004: Provider, Datenfluss und Prompt-Sicherheitsmodell

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

Provider werden in drei Adaptergruppen getrennt:

1. Ollama und explizit erlaubte lokale OpenAI-kompatible Loopback-Endpoints;
2. native OpenAI-API unter `https://api.openai.com/v1`;
3. OpenRouter unter `https://openrouter.ai/api/v1`.

OpenRouter-Modell-IDs bleiben frei konfigurierbar. Dadurch können GPT-5.6 Luna, DeepSeek oder Anthropic-Modelle verwendet werden, ohne eine konkrete, möglicherweise veränderliche Provider-ID in den Code zu binden.

Alle Adapter erfüllen denselben Vertrag für Messages, Modell, Sampling, Context-Limit, Structured Output, Streaming, Token/Kosten und normalisierte Fehler. API-Keys werden ausschließlich über Environment-Variablen referenziert.

Ein externer Datenfluss benötigt eine einmalige Aktivierung im Inspector. Provider, Endpoint, Modell oder State-Binding-Änderungen invalidieren diese Aktivierung.

## Prompt- und Retrieval-Regeln

```text
globaler Prompt
→ agents.md / lokaler Prompt
→ Node-Prompt
→ dynamische State-Variablen
```

RAG-Treffer und Tool-Outputs sind `untrusted_context`, niemals Systemanweisungen. Sie dürfen keine Systeminstruktionen, Graph-Topologie, Tool-Konfiguration oder Berechtigungen überschreiben. Nur begrenzte sichere Variablenersetzung, kein arbitrary Jinja oder Codeausführung.

## Begründung

HarnessForge verbindet private Workspace-Daten, untrusted Inhalte und potenziell externe Kommunikation. Explizite Datenfluss-Aktivierung, feste Endpoint-Allowlist und Least Privilege reduzieren den LLM-/Agentic-Lethal-Trifecta-Risikopfad.

## Konsequenzen

- Beliebige externe Base-URLs sind im MVP gesperrt.
- Redirects, Timeouts und Responsegrößen werden erneut geprüft.
- Token, Auth-Header, Secrets und sensible Inhalte werden aus Logs redigiert.
- Ein vollständiger Prompt-Injection-Schutz wird nicht behauptet; Schadensbegrenzung und strukturierte Outputs sind verpflichtend.
- Guardrail-Node, MCP und weitergehende Agenten-Governance bleiben Phase 2.
