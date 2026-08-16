# HarnessForge

> **Forge your autonomous agents with deterministic precision.**

HarnessForge ist ein lokales, browserbasiertes Werkzeug für KI-Entwickler und Agent Engineers. Agent-Harnesses werden als sichtbare State-Graphen entworfen, lokal ausgeführt, beobachtet und als eigenständige Python-Runner exportiert.

Dieses Repository enthält die Produktplanung und eine getestete MVP-Grundimplementierung der Backend-/Frontend-Slices.

## Vision

HarnessForge macht die bisher schwer sichtbare Laufzeit eines Agenten nachvollziehbar:

- Graphen, Loops und State-Mutationen werden visuell modelliert.
- `agents.md`, lokale Prompts und LanceDB-Daten bleiben zunächst im Workspace.
- Ausführung, Iterationen, RAG-Treffer, Tool-Ergebnisse und LLM-Streaming werden live sichtbar.
- harte Budgets verhindern unbounded loops, Tool-DoS und unbounded state growth.
- ein Graph kann als eigenständiges `agent_runner.py`-Bundle exportiert werden.

Das Produkt ist im MVP **100 % localhost, Single-User und ohne Cloud-Zwang**. Externe LLM-Provider sind ausdrücklich konfigurierbare Datenabflussziele und werden transparent behandelt.

## MVP-End-to-End-Flow

1. Einen Workspace auswählen.
2. Einen Graphen im Canvas erstellen: `Start -> ... -> Output`.
3. Einen lokalen Prompt bzw. `agents.md` anbinden.
4. Read-only-LanceDB-Retrieval konfigurieren.
5. LLM-, Reducer-, Loop- und Tool-Nodes verbinden.
6. Graph validieren und aktivieren.
7. Auf localhost ausführen und Live-Trace/Node-Glow beobachten.
8. Einen validierten Graphen mit einem Klick als Runner-Bundle exportieren.

## MVP-Node-Typen

- `Start`
- `LLM Call`
- `RAG / LanceDB` (read-only)
- `Loop / Router`
- `State Reducer`
- `Tool` (lokaler Subprozess im transparenten Local Trust Mode)
- `Output`

Human-Gates, Sub-Graphs, MCP-Autodiscovery, Guardrail-Nodes, Time-Travel-Debugging und stärkere Sandbox-Optionen sind Phase-2-Ziele und im MVP nicht aktiviert.

## Zielplattform und Technologieentscheidungen

- **Frontend:** Vite, React, TypeScript, XYFlow/React Flow, Tailwind CSS, Zustand
- **Backend:** Python, FastAPI
- **Persistenz:** Git-diffbare `.forge.json`, SQLite unter `.harnessforge/runs.db`
- **RAG:** vorhandene LanceDB-Verzeichnisse und Tabellen, read-only
- **Runner:** eigenständiges async Python, `httpx`, `lancedb`, `pydantic`
- **Primäre Sicherheitsplattform:** Linux/Unix
- **Netzwerk:** Backend bindet ausschließlich an `127.0.0.1`

Die Modular-Monolith-/VSA-Struktur ist verbindlich in [`CONTEXT.md`](CONTEXT.md), [`docs/PLAN.md`](docs/PLAN.md) und [`docs/adr/ADR-001-vsa-modular-monolith.md`](docs/adr/ADR-001-vsa-modular-monolith.md) beschrieben.

## Provider

Es gibt drei klar getrennte Adaptergruppen:

1. **Lokale Server:** Ollama und OpenAI-kompatible lokale Endpoints für vLLM, LM Studio oder llama.cpp. Nur explizit freigegebene Loopback-Ziele sind im MVP erlaubt.
2. **Native OpenAI:** offizielle API unter `https://api.openai.com/v1`, Secret über `$OPENAI_API_KEY`.
3. **OpenRouter:** dedizierter Adapter unter `https://openrouter.ai/api/v1`, Secret über `$OPENROUTER_API_KEY`, optional mit Referer-/Title-Headern.

OpenRouter-Modell-IDs sind frei konfigurierbar, damit etwa GPT-5.6 Luna, DeepSeek oder Anthropic-Modelle genutzt werden können. Der Anzeigename wird nicht mit einer möglicherweise veränderlichen Provider-ID verwechselt; eine konkrete ID wird nicht fest in die Architektur eingebaut.

API-Keys stehen niemals in `.forge.json`, Logs, Trace-Daten oder dem exportierten Code.

## Sicherheit in Kurzform

- Workspace-Zugriff wird über aufgelöste Realpfade begrenzt; Traversal, Symlink-Escapes und sensible Systemdateien sind gesperrt.
- Importierte Graphen starten im Review-/Read-only-Modus und benötigen eine explizite Aktivierung.
- Provider-, Datenbinding- und Tool-Aktivierungen werden bei Konfigurationsänderungen invalidiert.
- Das Backend verwendet ein zufälliges Session-Token pro Start, restriktives CORS und Host-Header-Prüfung.
- RAG- und Tool-Inhalte werden als `untrusted_context` behandelt und überschreiben keine Systemanweisungen.
- Tools laufen im MVP im sichtbaren **Local Trust Mode**, nicht in einer vollständig isolierten Sandbox.
- Tool-Timeout, Output-Cap, Run-Dauer, Node-Anzahl, Loop-Schritte und State-Größe haben unveränderliche Hard-Caps.
- Logs sind standardmäßig gekürzt und redigiert; vollständige Snapshots sind nur im expliziten lokalen Debug-Modus erlaubt.
- Keine Telemetrie; Run-Retention beträgt standardmäßig 30 Tage und ist löschbar.

Details und Sicherheits-Gates stehen in [`docs/PLAN.md`](docs/PLAN.md) und den ADRs.

## Geplantes Export-Bundle

Ein erfolgreicher Export erzeugt:

```text
agent_runner.py
requirements.txt
.env.example
```

Der Runner enthält die validierte Graph-Topologie, bietet eine `argparse`-CLI, stdout-Streaming, JSON-Logs, saubere Exit-Codes und `--dry-run`. Er importiert weder FastAPI noch React oder das HarnessForge-Backend. Dependencies werden exakt gepinnt.

## Geplante Dokumentation

- [`idea.md`](idea.md) — ursprüngliche Produktidee
- [`CONTEXT.md`](CONTEXT.md) — Domänenvokabular und Architekturbegriffe
- [`docs/PLAN.md`](docs/PLAN.md) — Phasen, Slices, Meilensteine, Tests und Gates
- [`docs/RELEASE_AUDIT.md`](docs/RELEASE_AUDIT.md) — verifizierter Release-Stand und offene Gates
- [`docs/adr/`](docs/adr/) — Architecture Decision Records

## Geplanter lokaler Quickstart

> Die folgenden Befehle sind der lokale Entwicklungs-Quickstart.

```text
1. Repository und geplante Dependencies installieren.
2. Backend ausschließlich auf 127.0.0.1 starten.
3. Frontend im Desktop-Browser öffnen.
4. Workspace auswählen und Graph erstellen oder eine .forge.json importieren.
5. Graph validieren, Provider/Datenfluss und Tools explizit aktivieren.
6. Run starten oder das Bundle exportieren.
```

## Qualitätsziel

Vor der MVP-Freigabe müssen Backend- und Frontend-Slices Unit- und Integrationstests besitzen. Kritische Security- und Exportpfade müssen vollständig grün sein. Architektur-Fitness-Tests sichern die VSA-Grenzen; jeder behobene Bug oder Security-Fund erzeugt einen dauerhaften Regressionstest (Ratchet-Prinzip).

## Status

- Produktplanung: bestätigt
- Dokumentation: angelegt
- Implementierung: Backend-/Frontend-Slices vorhanden und getestet
- Status: MVP-Entwicklung mit verbleibenden Provider-/UI-Erweiterungen
