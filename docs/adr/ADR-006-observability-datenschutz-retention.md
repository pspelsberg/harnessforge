# ADR-006: Observability, Datenschutz und Run-Retention

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

Live-Events werden per WebSocket mit Session-Token und Origin-Prüfung übertragen und zusätzlich normalisiert in `.harnessforge/runs.db` persistiert. Erfasst werden Run-/Node-Status, Iterationen, RAG-Scores, Tool-Exitcodes, LLM-Streaming und Fehlerzustände.

Events und Snapshots sind standardmäßig gekürzt und redigiert. Secrets, Auth-Header und bekannte Tokenmuster werden maskiert. Vollständige unzensierte State-Snapshots sind nur bei explizit aktiviertem lokalem Debug-Modus erlaubt.

Es gibt keine Telemetrie. Run-Daten werden standardmäßig 30 Tage behalten; die Retention ist konfigurierbar und jeder Run bzw. alle Runs können sofort gelöscht werden.

## Begründung

Observability ist für Debugging und Live-Glow notwendig, darf aber keine versteckte Datenbank für Prompts, PII oder Secrets werden. Privacy-by-default und Löschbarkeit sind daher Kernverträge.

## Konsequenzen

- Event- und Nachrichten-Größen besitzen feste Grenzen.
- Frontend rendert Plaintext/strukturiertes JSON, kein ungeprüftes Markdown.
- Datenfluss lokal/external und Debug-Modus werden sichtbar angezeigt.
- Externe Provider-Requests enthalten nur ausdrücklich gebundene State-Felder.
- DSGVO-/EU-AI-Act-Pflichten werden bei personenbezogenen/externalen Daten als Compliance-Trigger dokumentiert und geprüft.
