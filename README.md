# ⚡ HarnessForge

<div align="center">

![HarnessForge Logo](assets/logo.jpg)

### **Forge your autonomous agents with deterministic precision.**

*Visuelles State-Graph- & Loop-Engineering für autonome KI-Agenten direkt auf localhost.*  
*Kein Cloud-Zwang. Kein Vendor-Lock-in. Deterministische Kontrolle.*

[![Backend Tests](https://img.shields.io/badge/Backend%20Pytest-271%20Passed-10b981?style=flat-square&logo=pytest)](file:///home/peppi/coding/Harnessforge/backend)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Vitest-49%20Passed-10b981?style=flat-square&logo=vitest)](file:///home/peppi/coding/Harnessforge/frontend)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith%20(VSA)-f59e0b?style=flat-square)](file:///home/peppi/coding/Harnessforge/docs/adr/ADR-001-vsa-modular-monolith.md)
[![Security Standard](https://img.shields.io/badge/Security-CodeUltra%20Full%20Tier-38bdf8?style=flat-square)](file:///home/peppi/coding/Harnessforge/docs/PLAN.md)
[![License](https://img.shields.io/badge/License-MIT-slate?style=flat-square)](file:///home/peppi/coding/Harnessforge)

</div>

---

## 🧭 Was ist HarnessForge?

**HarnessForge** ist eine lokale No-Code/Low-Code-Entwicklerplattform, mit der du komplexe **Agent-Harnesses** (Scaffoldings) visuell im Browser entwirfst, lokal ausführst, in Echtzeit beobachtest und mit einem Klick in **eigenständigen, produktionsreifen Python-Code (`agent_runner.py`)** exportierst.

Statt generischer Automatisierungs-Tools (wie n8n) oder starrer Cloud-Wrapper (wie Dify) ist HarnessForge speziell für **Loop-Engineering**, **Graph-Engineering**, **lokale RAG-Pipelines (LanceDB)** und **lokale Prompt-Bindings (`agents.md`)** optimiert.

```
+------------------------------------------------------------------------------------+
|                                    HARNESSFORGE                                    |
|                                                                                    |
|  [ File Explorer ]  [ Canvas: React Flow + Custom Nodes ]   [ Live Inspector ]    |
|  - agents.md        ┌───────────┐    ┌──────────────┐       - Node Config         |
|  - prompts/         │ RAG Node  ├───►│ LLM Call     ├─┐     - State Diff          |
|  - lancedb_data/    │ (LanceDB) │    │ (agents.md)  │ │     - Token Counter       |
|  - tools/           └───────────┘    └──────▲───────┘ │     - Dataflow Approval   |
|                                             │         ▼                           |
|                                       ┌─────┴───────────┐                         |
|                                       │ Loop / Router   │◄─── [ State Reducer ]   |
|                                       │ (Max 5 Steps)   │                         |
|                                       └────────┬────────┘                         |
|                                                ▼                                  |
|                                       ┌─────────────────┐                         |
|                                       │ Output / Export │                         |
|                                       └─────────────────┘                         |
|  [ Bottom Drawer: Live Trace | Token Radar | Tool Output | Run History ]          |
+------------------------------------------------------------------------------------+
```

---

## ✨ Kern-Features

### 🎨 Visueller Flow-Canvas im Neural-Forge Darkmode
* **React Flow (XYFlow) Engine:** Flüssiges Drag-and-Drop, Zoom, Pan, Fit-to-View, Minimap und Tastatur-Shortcuts (`Ctrl+Z`, `Ctrl+Y`, `Del`, `Ctrl+D`).
* **Spezialisierte Node-Registry:**
  * **`Start Node`**: Graph-Einstiegspunkt mit Eingabe-Schema.
  * **`LLM Call Node`**: Dateipfad-Picker für lokale `agents.md` / Prompts; Auswahl lokaler Modelle (Ollama, vLLM) oder Cloud-APIs (OpenAI, OpenRouter z. B. GPT-5.6 Luna).
  * **`RAG / LanceDB Node`**: Liest lokale `.lance`-Verzeichnisse read-only aus; unterstützt Vektor- & Hybrid-Suche mit Score-Normalisierung.
  * **`Loop & Router Node`**: ReAct- & Reflexions-Zyklen per Klick mit deklarativen Bedingungen (`==`, `regex`, numeric, exists), harter `max_iterations`-Bremse und Pflicht-Fallback.
  * **`State Reducer Node`**: Deterministische State-Mutationen (`SET`, `APPEND_LIST`, `MERGE_DICT`, `INCREMENT`).
  * **`Tool Node`**: Führt lokale Bash- und Python-Skripte im transparenten **Local Trust Mode** mit Timeout und Output-Caps aus.
  * **`Output Node`**: Validierter Endzustand und strukturierte Rückgabe.
* **Dynamische Status-Glows:** Nodes leuchten live auf (`Amber Pulse` bei Ausführung, `Emerald` bei Erfolg, `Crimson` bei Fehlern).

### 🐍 1-Klick Standalone Python-Export (Zero Runtime Lock-in)
* Exportiert den gesamten Graphen in ein **einzelnes, autarkes Python-Skript (`agent_runner.py`)**.
* Null Abhängigkeiten zu FastAPI, React oder HarnessForge-Servern.
* Inklusive `argparse`-CLI, stdout-Streaming, JSON-Logs, sauberer Exit-Codes und `--dry-run`-Modus.
* Erzeugt automatisch ein gepinntes `requirements.txt` und `.env.example`.

### 🛡️ Robuste Sicherheits-Architektur (CodeUltra Full Tier)
* **Localhost-Only:** Backend bindet strikt an `127.0.0.1` mit zufälligem Session-Token pro Start und Host-Header-Schutz.
* **Workspace Boundary (F-PATH):** Alle Dateizugriffe werden über `os.path.realpath` validiert; `..`-Traversal, Symlink-Escapes, `.env` und `.ssh/` sind gesperrt.
* **Lethal-Trifecta-Schutz:** Explizite Bestätigung vor externen Provider-Aufrufen mit sichtbarer Datenfluss-Anzeige.
* **Untrusted Context Isolation:** RAG-Chunks und Tool-Outputs werden als `<untrusted_context>` isoliert, um Prompt Injections abzuwehren.
* **Tool Subprocess Governance:** SHA256-`config_hash`-Freigabe, 15s Default-Timeout (60s Hard-Cap), 50 KB Output-Cap und Prozessgruppen-Terminierung (`os.setsid`).

### 📊 Live Observability & Token-Radar
* **WebSocket-Event-Streaming:** Echtzeit-Updates für Node-Zustände, Streaming-Tokens, Tool-Outputs und Iterationen.
* **Token-Radar:** Aufschlüsselung des Context-Windows (System-Prompt, RAG-Chunks, Tool-Ergebnisse, Chat-Historie).
* **Lokale SQLite-Persistenz:** Speicherung aller Runs und redigierter Events unter `.harnessforge/runs.db` (WAL-Modus) mit 30-Tage-Retention und Ein-Klick-Löschung.

---

## 🏗️ Architektur & Tech-Stack

HarnessForge ist als **Modular Monolith mit Vertical Slice Architecture (VSA)** aufgebaut:

```text
Harnessforge/
├── assets/                             # Logos & Visual Assets (Neural Forge Emblem)
├── backend/
│   ├── app/
│   │   ├── core/                       # Skeleton: Config, Security Primitives, DB
│   │   └── features/                   # Tissue: Unabhängige Feature-Slices
│   │       ├── graph_authoring/        # .forge.json Schema & Validierung
│   │       ├── execution/              # Async Graph-Interpreter & Cycle Governance
│   │       ├── providers/              # Ollama, OpenAI, OpenRouter Adapters
│   │       ├── retrieval/              # LanceDB Read-only RAG & Context Isolation
│   │       ├── tool_execution/         # Subprocess Runner & Local Trust Mode
│   │       ├── observability/          # WebSocket Streaming & SQLite Store
│   │       └── export/                 # Standalone agent_runner.py Generator
│   ├── tests/                          # 271 automatisierte Tests (Pytest)
│   └── run.py                          # Unterstützter Launcher (127.0.0.1:8000)
├── frontend/
│   ├── src/
│   │   ├── app/                        # Layout & Shell
│   │   ├── shared/                     # Theme Tokens, UI Primitives, Session Auth
│   │   └── features/                   # Frontend Slices (Canvas, Inspector, Drawer)
│   └── package.json                    # Vite + React + Tailwind v4 + XYFlow
├── templates/
│   └── standalone_runner.py.jinja      # Jinja2-Vorlage für den Python-Export
├── docs/                               # Spezifikation, ADRs & PLAN.md
├── CONTEXT.md                          # Domänenvokabular & Invarianten
├── task.md                             # Master Implementation Task Board
└── Erweiterungen.md                    # Phase-2 Roadmap (RLM, REPL, MCP)
```

---

## 🚀 Schnellstart (Lokale Installation)

### Voraussetzungen
* **Python 3.12+** und [uv](https://docs.astral.sh/uv/) (empfohlen) oder `pip`
* **Node.js 20+** und `npm`
* *(Optional)* Lokales [Ollama](https://ollama.com/) für 100 % kostenlose lokale Inferenz

### 1. Backend starten
```bash
cd backend
uv sync
python run.py
```
> Das Backend läuft nun geschützt unter `http://127.0.0.1:8000`.

### 2. Frontend starten
```bash
cd frontend
npm install
npm run dev
```
> Öffne `http://localhost:5173` in deinem Desktop-Browser.

---

## 🧪 Test-Suites ausführen

Alle Komponenten sind durch automatisierte Unit-, Integrations- und Architektur-Fitness-Tests abgedeckt:

```bash
# Backend-Tests (271 Tests inkl. Security-Matrix & VSA-Boundary-Checks)
cd backend && uv run pytest

# Frontend-Tests (49 Vitest Component- & Store-Tests)
cd frontend && npm test -- --run

# Frontend Production Build prüfen
cd frontend && npm run build
```

---

## 📖 Dokumentation & weiterführende Links

* [idea.md](idea.md) — Ursprüngliches Produktkonzept und Tailwind v4 Farb-Tokens.
* [CONTEXT.md](CONTEXT.md) — Domänenvokabular, Begriffsdefinitionen und Invarianten.
* [docs/PLAN.md](docs/PLAN.md) — Detaillierter 8-Phasen-Implementierungsplan und CodeUltra-Gates.
* [docs/adr/](docs/adr/) — Architecture Decision Records (ADR-001 bis ADR-007).
* [task.md](task.md) — Master Implementation Task Board.
* [Erweiterungen.md](Erweiterungen.md) / [Erweiterungen_task.md](Erweiterungen_task.md) — Phase-2 Roadmap (RLM Prime-Agent-Pattern, Python-REPL-Sandbox, MCP-Gateway, Time-Travel-Debugger).

---

## 📄 Lizenz

MIT License — Erstellt mit Leidenschaft für Entwickler autonomer Agenten-Systeme.  
*Forge your autonomous agents with deterministic precision.*
