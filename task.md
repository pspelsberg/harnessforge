# 📋 HarnessForge — Master Implementation Task Board (`task.md`)

> **Status:** Bereit für die Implementierung  
> **Architektur-Modell:** Modular Monolith mit Vertical Slice Architecture (VSA)  
> **Sicherheits-Standard:** CodeUltra Full Tier (OWASP 2025, ASI01–ASI10, Least Privilege, DoS-Guards)  
> **Design:** Modern Forge Darkmode (Tailwind CSS v4, Obsidian `#0b0f17`, Amber Glow `#f59e0b`, Cyan `#38bdf8`)

---

## 🎯 Definition of Done (DoD) für jeden Task
Jeder Slice / Task gilt erst als abgeschlossen, wenn:
1. Der Code modular im jeweiligen VSA-Slice liegt (`backend/app/features/<slice>/` bzw. `frontend/src/features/<slice>/`).
2. `backend/app/core/` keine Feature-Implementierungen importiert (Architektur-Fitness).
3. Öffentliche Schnittstellen und Pydantic-Schemas typ- und validierungssicher sind (C-VAL).
4. Unit- und Integrationstests (Pytest / Vitest) geschrieben und 100 % grün sind.
5. Relevante Security-Regeln (Path-Sanitizing, Secret-Redaction, SSRF-Guards, Untrusted-Context) greifen.
6. Keine Secrets, Tokens oder unzensierte Stacktraces in Logs oder Export-Dateien gelangen.

---

## 🏗️ Phase 0: Foundation, Schemas, Security Baseline & Tooling

- [x] **0.1 Projekt-Initialisierung & VSA-Verzeichnisstruktur**
  - [x] Backend-Projektstruktur anlegen (`backend/app/core/`, `backend/app/features/`, `backend/tests/`)
  - [x] Frontend-Projektstruktur mit Vite + React + TypeScript anlegen (`frontend/src/features/`, `frontend/src/shared/`)
  - [x] Poetry / `requirements.txt` für Backend mit exakt gepinnten Dependencies aufsetzen (`fastapi`, `uvicorn`, `pydantic>=2.0`, `lancedb`, `httpx`, `aiosqlite`, `jinja2`, `pytest`, `pytest-asyncio`)
  - [x] Frontend `package.json` aufsetzen (`@xyflow/react` / React Flow, `tailwindcss@latest`, `lucide-react`, `zustand`, `clsx`, `tailwind-merge`, `vitest`)

- [x] **0.2 Versioniertes Graph-Schema (`.forge.json` Schema v1)**
  - [x] Pydantic Model `ForgeGraphSchema` definieren (`schema_version: "1"`, `id`, `name`, `workspace_path`, `nodes`, `edges`, `settings`)
  - [x] Strikte Trennung zwischen Runtime-Konfiguration (`node.data.config`) und UI-Metadaten (`node.position`, `node.data.ui`)
  - [x] JSON-Schema Export & Schema-Validierungstests implementieren

- [x] **0.3 Localhost-Sicherheitsarchitektur & Session-Schutz**
  - [x] Backend-Server so konfigurieren, dass er ausschließlich an `127.0.0.1` bindet (niemals `0.0.0.0`)
  - [x] Kryptografisch sicheres Session-Token (CSPRNG) beim Serverstart generieren
  - [x] Fast-API Middleware für Header-Prüfung (`X-HarnessForge-Token`) und WebSocket-Handshake-Auth
  - [x] Restriktive CORS-Middleware konfigurieren (ausschließlich lokaler Frontend-Origin, kein Wildcard `*`, keine Wildcard-Credentials)
  - [x] Host-Header-Validierung zur Abwehr von DNS-Rebinding-Angriffen einrichten

- [x] **0.4 Workspace Boundary & Path Sanitizer (CWE-22 / F-PATH)**
  - [x] `WorkspaceBoundaryService` in `backend/app/core/security/path_sanitizer.py` implementieren
  - [ ] Auflösung über `os.path.realpath` / `Path.resolve(strict=True)` zur Verhinderung von Symlink-Escapes
  - [ ] Automatische Ablehnung von `..`-Traversal, System-Verzeichnissen (`/etc`, `/usr`, `/proc`), `.env`, `.ssh/`, `.git/`
  - [x] Unit-Tests für Traversal-, Symlink- und Null-Byte-Angriffe schreiben

- [x] **0.5 Architektur-Fitness & Ratchet-Tests (F-FIT)**
  - [x] Automatisierte Import-Linter-Regel / Pytest-Architekturtest schreiben:
    - [x] `backend/app/core/` darf keine Module aus `backend/app/features/` importieren
    - [ ] Feature-Slices dürfen keine internen privaten Module anderer Feature-Slices importieren (nur öffentliche Verträge)
    - [ ] Der Standalone-Code-Generator darf kein `fastapi` oder `react` in den Export einbinden

---

## 🎨 Phase 1: Frontend Canvas & Graph Authoring Slice

- [x] **1.1 Tailwind CSS v4 & Neural Forge Design Tokens**
  - [x] `frontend/src/index.css` mit den offiziellen Farb-Tokens einrichten:
    - `--color-forge-canvas: #0b0f17` (Deep Obsidian Graphite Canvas)
    - `--color-forge-panel: #111827` (Dark Slate Sidebar/Inspector)
    - `--color-forge-node-bg: #151d2a` (Dark Steel Node Body)
    - `--color-forge-border: #334155` (Sharp Comic Outline)
    - `--color-forge-amber: #f59e0b` (Forge Fire Glow / Active Step)
    - `--color-forge-cyan: #38bdf8` (RAG LanceDB Data Streams)
    - `--color-forge-gold: #fcd34d` (Pulse Data Edges)
  - [x] Logo [`assets/logo.jpg`](file:///home/peppi/coding/Harnessforge/assets/logo.jpg) im App-Header einbinden

- [x] **1.2 React Flow Canvas Engine (`FlowCanvas.tsx`)**
  - [x] Infinite Zoom, Pan, Fit-to-View, Mini-Map und Dot-Grid (`#1e293b`)
  - [x] Drag-and-Drop Node-Palette aus der linken Sidebar
  - [x] Tastatur-Shortcuts: Undo (`Ctrl+Z`), Redo (`Ctrl+Y`), Löschen (`Del`/`Backspace`), Duplizieren (`Ctrl+D`)
  - [x] Export / Import Dialog für `.forge.json` mit automatischem Review-Modus für importierte Dateien

- [x] **1.3 Custom Node Registry (Visual Anatomy & Handles)**
  - [x] `StartNode.tsx` (Start-Trigger, Input-Schema)
  - [x] `LLMNode.tsx` (Model-Selector, Temperature, File-Picker für `agents.md`, Prompt-Vorschau)
  - [x] `RAGNode.tsx` (LanceDB Path Picker, Table Dropdown, Top-K, Distance Metric)
  - [x] `LoopNode.tsx` (Condition Editor, True/False-Handles, Max Iterations, Fallback-Handle)
  - [x] `ReducerNode.tsx` (Action: `SET`/`APPEND_LIST`, Source-Path, Target-State-Key)
  - [x] `ToolNode.tsx` (Script-Picker, Args, Output-Limits, "Local Trust Mode"-Badge)
  - [x] `OutputNode.tsx` (Endzustand, Final Output Payload)
  - [x] Dynamische Status-Glows pro Node: `Idle`, `Running (Amber Pulse)`, `Success (Emerald)`, `Error (Crimson)`

- [x] **1.4 Animierte Custom Edges (`ForgeEdge.tsx`)**
  - [x] SVG-Gradient-Kanten mit warmem Amber-Fluss (`#fcd34d` / `#fb923c`)
  - [x] Animierte Partikelbewegung bei aktivem Datenfluss
  - [x] Validierung visueller Verbindungsregeln (z. B. keine unzulässigen Cyclic-Verbindungen ohne Loop-Node)

- [x] **1.5 Inspector Panel & Local File System Explorer**
  - [x] Rechts angedockter, kollabierbarer Inspector für den selektierten Node
  - [x] Lokaler Dateisystem-Browser (liest Pfade & `.md`-Dateien sicher über Backend-API)
  - [x] Live-Anzeige der geschätzten Token-Verteilung (System Prompt, RAG Context, Tool Output)

- [x] **1.6 Graph Validation Engine (Frontend & Backend)**
  - [x] Dreistufige Validierung: `Error` (blockiert Run/Export), `Warning` (gelber Badge, blockiert Export standardmäßig), `Info`
  - [x] Validierungsregeln:
    - [x] Genau 1 Start- und 1 Output-Node vorhanden
    - [x] Keine verwaisten/unerreichbaren Nodes
    - [x] Jeder Loop-Node hat gültige Condition + Pflicht-Fallback-Zweig
    - [x] Alle referenzierten Dateien (`agents.md`, LanceDB, Tool-Skripte) existieren im Workspace
  - [x] Visuelle rote/gelbe Markierung fehlerhafter Nodes & Kanten direkt im Canvas

- [x] **1.7 Canvas State Management (Zustand) & Recovery**
  - [x] `useGraphStore` für Nodes, Edges, Selektion, History-Stack (Undo/Redo)
  - [x] Auto-Save im `localStorage` für Crash-Recovery (ohne Ausführungsberechtigung)
  - [x] Expliziter "Save"-Button für `.forge.json` ins Workspace-Verzeichnis

---

## ⚙️ Phase 2: Execution Engine & Cycle Governance Slice

- [x] **2.1 AgentState Model & Reducer Logic (`backend/app/features/execution/`)**
  - [x] Pydantic `AgentState` mit reservierten Standardfeldern:
    ```python
    messages: list[dict]
    query: str
    retrieved_context: list[dict]
    tool_results: list[dict]
    last_output: Any
    iteration: int
    metadata: dict
    custom_state: dict
    ```
  - [x] Reducer-Handler für atomare Mutationen: `SET`, `APPEND_LIST`, `MERGE_DICT`, `INCREMENT`
  - [x] Strikte Typprüfung & Pfadvalidierung (verhindert ungültige Keys und unkontrollierten State-Wuchs)

- [x] **2.2 Asynchroner Graph-Interpreter & Flow-Execution**
  - [x] Event-basierter Async-Runner für gerichtete Graphen
  - [x] Topologische Abarbeitung von Node zu Node
  - [ ] Statusübergänge: `created -> validating -> running -> succeeded / failed / cancelled / limit_exceeded`
  - [x] Einzelner aktiver Run pro HarnessForge-Prozess (neue Starts werden bei laufendem Run abgewiesen)

- [x] **2.3 Cycle Governance & Loop-Kontrolle (ReAct-Loops)**
  - [x] Deterministische Auswertung der Loop-Bedingung (String-Equals, Regex, Numeric Comparison, Key-Exists)
  - [x] Inkrementierung des Iterationszählers pro Zyklus
  - [x] Hard-Cap `max_iterations` (Default z. B. 5, konfigurierbar bis max. 50)
  - [x] Automatisches Umschalten auf den Pflicht-Fallback-Zweig bei Limitüberschreitung

- [x] **2.4 DoS-Schutz & Ressourcen-Hard-Caps (F-DOS)**
  - [x] Max. State-Größe: 5 MB Hard-Cap
  - [x] Max. Graph-Nodes: 50 Hard-Cap
  - [x] Max. Gesamt-Run-Dauer: 5 Minuten Timeout
  - [ ] Sofortiger sauberer Abbruch und Logging bei Budget-Überschreitung

- [x] **2.5 Sofortiger Run-Abbruch (Stop-Signal)**
  - [x] WebSocket-Befehl `run.cancel` empfangen
  - [ ] Laufende Subprozesse hart per Prozessgruppe (`SIGKILL` / `SIGTERM`) beenden
  - [ ] Aktive LLM-Streaming-Sockets sauber schließen
  - [ ] Status als `cancelled` in SQLite persistieren

---

## 🤖 Phase 3: Provider Slice (Ollama, Local, OpenAI, OpenRouter)

- [x] **3.1 Einheitlicher Chat-Completion Adaptervertrag (`providers/base.py`)**
  - [ ] Interface `BaseProviderAdapter` mit einheitlicher Methode `async def complete(request: CompletionRequest) -> AsyncIterator[CompletionChunk]`
  - [ ] Einheitliche Datenstruktur für Tokens, Kosten-Metadaten und normalisierte Fehlermeldungen

- [x] **3.2 Provider-Adapter Implementierungen**
  - [ ] `OllamaAdapter`: Anbindung an lokales Ollama (`http://127.0.0.1:11434/api/chat`)
  - [ ] `LocalOpenAIAdapter`: Für vLLM, LM Studio, llama.cpp mit konfigurierbarer Loopback-URL
  - [ ] `NativeOpenAIAdapter`: Offizielle OpenAI-API (`https://api.openai.com/v1`)
  - [ ] `OpenRouterAdapter`: OpenRouter-API (`https://openrouter.ai/api/v1`) inkl. GPT-5.6 Luna / dynamischer Modell-ID und optionalen Referer-/Title-Headern

- [x] **3.3 SSRF-Schutz & Endpoint-Allowlist (F-PATH / SSRF)**
  - [ ] Strikte Host-Validierung für Provider-URLs:
    - Erlaubt: `127.0.0.1:*`, `localhost:*`, `api.openai.com`, `openrouter.ai`
    - Verboten: Private LAN-IPs (10.x, 192.168.x, 172.16.x) und Cloud-Metadata-IPs (`169.254.169.254`)
  - [x] Keine unkontrollierten HTTP-Redirects

- [x] **3.4 Secret Redaction & Key-Management Policy (F-SEC / C-LOG)**
  - [x] API-Keys werden ausschließlich über Environment-Variablen geladen (`$OPENAI_API_KEY`, `$OPENROUTER_API_KEY`)
  - [ ] Niemals Plaintext-Keys in `.forge.json`, Event-Logs, WebSocket-Streams oder exportiertem Code
  - [ ] Automatischer Regex-Maskierer für Bearer-Tokens & Auth-Header in allen Trace-Logs

- [ ] **3.5 Lethal-Trifecta-Schutz & Datenfluss-Aktivierung**
  - [ ] UI-Dialog zur expliziten Datenfluss-Aktivierung vor dem ersten Request an externe Provider
  - [ ] Klare Anzeige, welche State-Felder an den externen Provider gesendet werden
  - [ ] Automatische Invalidierung der Freigabe bei Änderungen an Provider, Modell, Endpoint oder State-Bindings

- [x] **3.6 Prompt Binding & Variable Interpolation**
  - [ ] Sichere Prompt-Prioritätskette: `globaler Prompt -> agents.md -> Node-Prompt -> State-Variablen`
  - [ ] Sichere String-Formatierung (`{query}`, `{retrieved_context}`, `{last_output}`) ohne unsicheres `eval()` / arbitrary Jinja-Code

---

## 📚 Phase 4: Retrieval Slice (LanceDB Read-Only RAG)

- [x] **4.1 Lokaler LanceDB Inspector (`retrieval/lancedb_inspector.py`)**
  - [ ] Öffnet lokales LanceDB-Verzeichnis innerhalb der Workspace-Boundary
  - [ ] Listet Tabellennamen auf und liest Spalten-Metadaten aus
  - [ ] Auto-Erkennung von Text- und Vektorspalten

- [x] **4.2 LanceDB Query Runner (`retrieval/lancedb_runner.py`)**
  - [ ] Führt Vektor-Suche und optionale Hybrid-Suche (Dense + BM25) aus
  - [x] Normalisiert Treffer-Ergebnisse:
    ```python
    [{"text": str, "score": float, "metadata": dict}]
    ```
  - [x] Hard-Caps für Trefferzahl (Top-K max. 20) und maximale Chunk-Länge

- [x] **4.3 Untrusted Context Isolation (F-LLM / Prompt Injection Guard)**
  - [x] RAG-Treffer werden im Prompt strukturell als `<untrusted_context>` eingekapselt
  - [ ] System-Prompt stellt klar, dass RAG-Inhalte reine Referenzdaten sind und keine Steuerbefehle überschreiben dürfen
  - [ ] RAG-Inhalte dürfen niemals Systemprompts, Graph-Topologie oder Tool-Freigaben manipulieren

---

## 🛠️ Phase 5: Tool Execution Slice (Local Trust Mode Sandbox)

- [x] **5.1 Workspace-Bounded Subprocess Runner (`tool_execution/runner.py`)**
  - [ ] Ausführung lokaler Skripte (`.py`, `.sh`, `.js`) innerhalb des Workspaces
  - [x] `shell=False` als Pflicht-Standard (keine unkontrollierten Shell-Interpolationen)
  - [ ] Arbeitsverzeichnis strikt auf den Workspace beschränkt

- [x] **5.2 "Local Trust Mode" Governance & Transparenz**
  - [ ] Sichtbare Warnung im Tool-Node: "Lokaler Vertrauensmodus (Subprozess ohne OS-Sandbox)"
  - [ ] Minimierte Environment-Vererbung (API-Keys und Session-Tokens werden standardmäßig aus `env` entfernt)
  - [x] Kontrollierte `PATH`-Umgebung

- [x] **5.3 Hash-basierte Tool-Freigabe (`config_hash`)**
  - [ ] Berechnung eines SHA256-Hashes über Skriptpfad, mtime/Inhalt, Argumente, Env-Allowlist, Schreibverzeichnisse und Limits
  - [ ] Tool darf nur ausgeführt werden, wenn der `config_hash` im Canvas manuell bestätigt wurde
  - [ ] Jede Datei- oder Konfigurationsänderung invalidiert den Status sofort

- [x] **5.4 Subprozess-Limits & Prozessgruppen-Terminierung (F-DOS)**
  - [x] Timeout: Default 15 Sekunden, Hard-Cap 60 Sekunden
  - [x] Output-Cap: Max. 50 KB für stdout und stderr (Überlauf wird trunkiert)
  - [ ] Erzeugung einer eigenen Prozessgruppe (`preexec_fn=os.setsid` unter Unix) für zuverlässiges Killen aller Child-Prozesse bei Timeout/Abbruch

- [ ] **5.5 Deklarative Schreibrechte (Allowlist)**
  - [ ] Standardmäßig rein read-only
  - [ ] Schreibrechte müssen explizit für deklarierte Workspace-Unterverzeichnisse aktiviert werden
  - [ ] Schreibversuche außerhalb des Workspaces oder in `.env`/Systempfade führen zum sofortigen Tool-Fehler

---

## 📡 Phase 6: Observability Slice (WebSocket & SQLite Persistence)

- [ ] **6.1 WebSocket Event Server (`observability/ws_server.py`)**
  - [ ] Authentifizierung via Session-Token im Handshake
  - [ ] Bidirektionale Events: Run starten, pausieren, abbrechen
  - [ ] Normalisierte Streaming-Events:
    - `node.queued`, `node.running`, `node.succeeded`, `node.failed`
    - `llm.token_stream`, `rag.results`, `tool.output`
    - `iteration.update`, `state.diff`, `run.completed`

- [ ] **6.2 Live UI Inspection & Trace Viewer (Bottom Drawer)**
  - [ ] Live-Highlighting des aktiven Knotens im Canvas (Forge Amber Pulse)
  - [ ] Terminal-Stream für LLM-Tokens und Tool-Logs
  - [ ] Token- und Budget-Radar (Visualisierung von System-, RAG- und History-Tokens)
  - [ ] Reines Text- und JSON-Rendering (kein `dangerouslySetInnerHTML` zur XSS-Vermeidung)

- [x] **6.3 Lokale SQLite Run-Persistenz (`observability/run_store.py`)**
  - [x] Persistierung unter `.harnessforge/runs.db` (SQLite im WAL-Modus)
  - [x] Gespeicherte Entitäten: `runs`, `events`, `checkpoints`
  - [ ] Standardmäßig gekürzte und redigierte Daten (Maskierung sensibler Strings)
  - [ ] Vollständige Snapshots nur bei explizitem lokalem Debug-Flag

- [x] **6.4 Privacy-by-Default & Retention-Policy (F-CMP / DSGVO)**
  - [ ] Keine externe Telemetrie oder Tracking
  - [x] Automatische Retention (Standard 30 Tage, konfigurierbar)
  - [x] UI-Aktionen: "Diesen Run löschen" und "Alle Runs unwiderruflich löschen"

---

## 🐍 Phase 7: Export Slice (Standalone Python Runner Bundle)

- [ ] **7.1 Export-Validierungs-Pipeline (`export/validator.py`)**
  - [ ] Strikte Prüfung vor Export: Blockiert Export bei unvollständigen Nodes, fehlenden Fallbacks oder ungültigen Pfaden
  - [x] Klare Fehlermeldungen statt stillem Ignorieren nicht unterstützter Nodes

- [ ] **7.2 Standalone Python Code Generator (`export/generator.py`)**
  - [ ] Jinja2-Template `templates/standalone_runner.py.jinja`
  - [ ] Generiert eigenständiges `agent_runner.py` mit:
    - [ ] Eingebetteter, validierter Graph-Topologie
    - [ ] Autarker Async-State-Machine
    - [ ] Provider-Aufrufen via `httpx`
    - [ ] LanceDB-Abfrage via nativem `lancedb`
    - [ ] Tool-Subprozess-Steuerung mit Timeout & Output-Cap
    - [x] `argparse`-CLI Interface (`--prompt`, `--workspace`, `--dry-run`, `--json-logs`)
    - [ ] Sauberem stdout-Streaming & Exit-Codes (0 bei Erfolg, 1 bei Abbruch, 2 bei Limit)
  - [x] Absolutes Null-Lock-in: Null Abhängigkeiten zu FastAPI, React oder HarnessForge-Servern

- [x] **7.3 Export Bundle Packaging**
  - [ ] Erzeugt `requirements.txt` mit exakt gepinnten Dependencies (`httpx==...`, `lancedb==...`, `pydantic==...`)
  - [ ] Erzeugt `.env.example` mit den benötigten Variablen (`OPENAI_API_KEY=`, `OPENROUTER_API_KEY=`)
  - [x] 1-Klick-Download im Browser als `.zip` oder Speichern im Workspace

---

## 🧪 Phase 8: Test-Suite, Security-Regressionen & End-to-End Release

- [x] **8.1 Backend Pytest Test-Suite**
  - [x] Unit-Tests für alle VSA-Feature-Slices (`tests/unit/`)
  - [x] Integrationstests mit Fake-Providern und Mock-Tools (`tests/integration/`)
  - [x] VSA-Architektur-Fitness-Tests (Prüfung auf illegale Cross-Slice-Imports)

- [x] **8.2 Frontend Vitest Test-Suite**
  - [x] Component-Tests für Canvas, Nodes, Edges und Inspector
  - [x] Zustand Store Action Tests (Undo/Redo, Validierungs-Status)

- [x] **8.3 CodeUltra Security Regression Matrix**
  - [x] `test_security_path_traversal.py`: `..`-Traversal, Symlink-Escapes, `.env`-Zugriffe abwehren
  - [x] `test_security_ssrf.py`: Blockieren privater LAN- und Cloud-Metadata-IPs bei Provider-Endpunkten
  - [x] `test_security_secret_redaction.py`: Keine API-Keys in Logs, Events, SQLite oder Export-Code
  - [x] `test_security_dos_limits.py`: Loop-Limit (50), Timeout (5 Min), State-Cap (5 MB), Tool-Timeout
  - [x] `test_security_untrusted_context.py`: RAG-Chunks und Tool-Outputs dürfen System-Prompts nicht überschreiben

- [ ] **8.4 End-to-End Verification Run**
  - [ ] Graph im Canvas erstellen: `Start -> LanceDB RAG -> LLM Call (agents.md) -> Loop (Max 3) -> State Reducer -> Tool -> Output`
  - [ ] Live-Ausführung auf localhost beobachten (Glow-Effekte, Streaming, SQLite-Events)
  - [ ] Standalone-Bundle exportieren und isoliert in einer frischen virtuellen Python-Umgebung ausführen:
    ```bash
    python agent_runner.py --prompt "Test-Task"
    ```
  - [ ] Überprüfen, ob das generierte Skript ohne Fehler durchläuft und den erwarteten Output liefert

---

*HarnessForge — Master Implementation Task Board.*
