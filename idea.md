# ⚡ HarnessForge — Local No-Code Agent Harness & Graph Forge

> **Visuelles State-Graph- & Loop-Engineering direkt auf localhost.**  
> Baue, teste, debugge und exportiere deterministische Agenten-Harnesses mit RAG (LanceDB), ReAct-Loops, State-Reducern, Sub-Agent-Firewalls und lokalem Prompt-Binding (`agents.md`).

---

## 🎨 Visual Identity & Offizielles Logo

Als offizielles Logo für **HarnessForge** wurde **Option 3: The Neural Forge Emblem** ausgewählt.

### 🏆 Offizielles Logo: The Neural Forge Emblem (`assets/logo.jpg`)
* **Artwork-Datei:** [assets/logo.jpg](file:///home/peppi/coding/Harnessforge/assets/logo.jpg) (Original: [assets/logo_option_3_neural_forge.jpg](file:///home/peppi/coding/Harnessforge/assets/logo_option_3_neural_forge.jpg))
* **Stil & Ästhetik:** Kreisrundes Tech-Abzeichen mit massivem Amboss, aus dem durch den Hammerschlag leuchtende Graph-Nodes, neuronale Schaltkreise und Cyber-Funkenströme emporsteigen.
* **Farbwelt:** Tiefes Obsidian-/Graphit-Dunkel, glühendes Schmiedefeuer-Amber (`#f59e0b` / `#fb923c`), warme Schaltkreis-Linien (`#d97706`) und Akzente in Cyber-Cyan & Steel-Slate.
* **Einsatzbereich:** App Header Badge, Desktop-Favicon, Loading-Animationen und Export-Watermarks.

---

## 🧭 Problemstellung & Vision

Moderne Agenten-Systeme scheitern in der Praxis meist nicht am LLM selbst, sondern am fehlenden oder unzureichenden **Harness** (Scaffolding):
1. **Endlosschleifen & Drift:** Agenten verheddern sich im ReAct-Loop ohne strikte Budgets und Fallbacks.
2. **Schwarze Kiste:** Man sieht nicht, welche Tokens aus RAG-Retrievern, System-Prompts oder Tool-Outputs den Context sprengen.
3. **Vendor-Lockin:** Viele No-Code-Tools zwingen Entwickler in proprietäre Cloud-Runtimes statt sauberen, eigenständigen Python-Code zu liefern.
4. **Schwieriges Debugging:** Wenn Step 7 fehlschlägt, muss der gesamte Workflow von vorn gestartet werden (teuer & zeitaufwändig).

**HarnessForge** löst dies als lokales Desktop-/Web-Tool:
* **Visual Graph & Loop Canvas:** Klicke State-Graphen, ReAct-Loops und RAG-Pipelines intuitiv zusammen.
* **Lokale First-Class Integration:** Liest `agents.md`, System-Prompts und LanceDB-Tabellen direkt aus deinem Dateisystem.
* **Zero Runtime Lock-in:** 1-Klick-Export in sauberes, produktionsreifes Python (`agent_runner.py`).
* **Time-Travel Debugger:** Springe in beliebige Checkpoints zurück, editiere den State live im Browser und führe den Graph ab dort weiter.

```
+------------------------------------------------------------------------------------+
|                                    HARNESSFORGE                                    |
|                                                                                    |
|  [ File Explorer ]  [ Canvas: React Flow + Custom Nodes ]   [ Live Inspector ]    |
|  - agents.md        ┌───────────┐    ┌──────────────┐       - Node Config         |
|  - prompts/         │ RAG Node  ├───►│ LLM Call     ├─┐     - State Diff          |
|  - lancedb_data/    │ (LanceDB) │    │ (agents.md)  │ │     - Token Counter       |
|  - tools/           └───────────┘    └──────▲───────┘ │                           |
|                                             │         ▼                           |
|                                       ┌─────┴───────────┐                         |
|                                       │ Loop / Evaluator│◄─── [ State Reducer ]   |
|                                       │ (Condition)     │                         |
|                                       └────────┬────────┘                         |
|                                                ▼                                  |
|                                       ┌─────────────────┐                         |
|                                       │ Output / Export │                         |
|                                       └─────────────────┘                         |
|  [ Bottom Drawer: Time-Travel Timeline | Streaming Logs | Token & Cost Radar ]    |
+------------------------------------------------------------------------------------+
```

---

## 🧱 Die Kern-Bausteine (Node Registry)

Jeder Node im Graph hat ein striktes Ein-/Ausgabe-Schema und interagiert mit dem globalen State Dict (`AgentState`).

| Node-Typ | UI-Konfiguration & Parameter | Lokale / System-Integration |
| :--- | :--- | :--- |
| **`LLM Call`** | • Model (Ollama / Local vLLM / OpenAI / Anthropic / Groq)<br>• Temperature, Top-P, Context Limit<br>• Structured Output Schema (Pydantic / JSON Schema)<br>• System Prompt Modus | Dateipfad-Picker für lokale `agents.md`, `system_prompt.txt` oder Jinja2-Templates mit Live-Hot-Reload. |
| **`RAG / LanceDB`** | • Vector DB Directory Path (z. B. `~/.lancedb` oder `./data`)<br>• Table Name & Embedding Model (`fastembed`, Ollama, etc.)<br>• Top-K, Distance Metric (Cosine/L2), Min-Score<br>• Hybrid Search (Dense + BM25 Sparse) & Reranking | Liest direkt aus lokalen `.lance` Verzeichnissen ohne separaten Datenbank-Server. |
| **`Loop & Router`** | • Condition Type (Python Expr, Regex, JSONPath, LLM-Judge)<br>• True-Target / False-Target Handle<br>• Safety: Max Iteration Count (z. B. 5), Token Ceiling<br>• Fallback Route bei Timeout / Parsing-Error | Verhindert Endlosschleifen und realisiert deterministische ReAct- und Reflexion-Zyklen. |
| **`Tool / Sandbox`** | • Tool Name & Schema (Args & Types)<br>• Execution Mode: Direct Subprocess, Docker, Podman, WASM<br>• Script Path (`.py`, `.sh`, `.js`) oder CLI Command<br>• Timeout & Error-Interception | Führt Skripte in isolierten Sandboxen aus; fängt Stderr ab und formatiert es als Observation für den State. |
| **`State Reducer`** | • Action: `SET`, `APPEND_LIST`, `MERGE_DICT`, `INCREMENT`, `DELETE`<br>• Source Path (z. B. `llm_call_1.output.result`)<br>• Target State Key (z. B. `messages`, `working_memory`) | Deterministische State-Mutation zwischen den Nodes; verhindert inkonsistente globale Zustände. |
| **`Human-Gate (HITL)`** | • Pause Condition (z. B. vor destruktiven Tool-Calls)<br>• Custom Approval Form (Input Text, Buttons: Approve, Reject, Edit)<br>• Notification & Webhook Hook | Hält die Graph-Ausführung an und wartet im Browser auf Benutzerinteraktion. |
| **`Sub-Graph`** | • Eingebetteter Child-Graph (z. B. Recherchier-Subagent)<br>• Port-Mapping (Input State -> Sub-Graph State -> Output State)<br>• Isolierter Kontext (Firewall) | Kapselt komplexe Sub-Workflows und verhindert Context-Pollution im Hauptgraphen. |
| **`Guardrail & Evaluator`** | • Prompt Injection Filter<br>• PII Redaction (Datenschutz)<br>• Output Validation & JSON Repair | Validiert Ein- und Ausgaben vor dem nächsten Schritt. |

---

## ⚡ Killer-Features & Differentiators

### 1. 🐍 Export to Standalone Code (`agent_runner.py`)
* Kein Lock-in: Der gesamte visuelle Graph wird per Knopfdruck in sauberen, asynchronen Python-Code exportiert.
* Verwendet pure Python Standardbibliothek + optionale native Bibliotheken (`lancedb`, `pydantic`, `httpx`).
* Inklusive CLI-Interface (`python agent_runner.py --prompt "..."`) und Dockerfile für sofortiges Deployment.

### 2. ⏳ Time-Travel Debugging & State Replay
* Bei jeder Node-Ausführung wird ein Snapshot des `AgentState` in SQLite/DuckDB gespeichert.
* Schlägt z. B. Loop 4 fehl:
  1. Klicke in der visuellen Zeitleiste auf Step 2 oder 3.
  2. Inspiziere den State zu diesem Zeitpunkt.
  3. Passe Variablen oder Prompt manuell an.
  4. Führe den Graph ab diesem Checkpoint neu aus.

### 3. 📊 Live Token & Budget Radar
* Farbcodierter Balken im Header und pro Node:
  * 🟦 **System Prompt & Agents.md:** Basis-Prompt-Größe.
  * 🟨 **RAG Context (LanceDB):** Injizierte Dokument-Chunks.
  * 🟩 **Tool Observations:** Ausgaben vorheriger Tools.
  * 🟪 **Chat History / Working Memory:** Historie der Turns.
* Sofortige Warnung, wenn das gewählte Modell-Limit (z. B. 8k / 32k / 128k) überschritten wird oder Kosten-Limits greifen.

### 4. 🔌 MCP (Model Context Protocol) Autodiscovery
* Erkennt lokale MCP-Server (z. B. Filesystem, Git, Postgres, SQLite, Custom MCPs).
* Wandelt gefundene MCP-Tools automatisch in sofort nutzbare Tool-Nodes auf dem Canvas um.

---

## 💻 Tech-Stack & Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Vite + React)                │
│  - XYFlow (React Flow) Canvas Engine                        │
│  - Tailwind CSS v4 (Modern Forge Dark Mode)                 │
│  - Zustand (Graph & UI State Management)                    │
│  - Monaco Editor / CodeMirror (Prompt & JSON Schema Editor) │
│  - Lucide Icons + Radix UI Primitives                       │
│  - WebSocket Client für Live-Graph-Streaming                │
└──────────────────────────────▲──────────────────────────────┘
                               │ HTTP / WebSocket (SSE)
┌──────────────────────────────▼──────────────────────────────┐
│                    BACKEND (Python / FastAPI)               │
│  - Async Graph Execution Runtime (Cyclic DAG Engine)        │
│  - Local FS Bridge (Directory Browser, File Watcher)        │
│  - LanceDB Native Engine (Local Vector Search)              │
│  - State Checkpointer (SQLite WAL Mode / In-Memory)         │
│  - Standalone Code Generator (Jinja2 Templates)             │
│  - Sandboxed Runner (Subprocess / Docker API)               │
└─────────────────────────────────────────────────────────────┘
```

### 🎨 Design System & Farbkonzept (Neural Forge Darkmode)

Basierend auf dem offiziellen Logo **Option 3: The Neural Forge Emblem** ist das UI-Farbkonzept in Tailwind CSS v4 wie folgt definiert:

```css
:root {
  /* Surface & Base Backgrounds */
  --color-forge-canvas: #0b0f17;       /* Deep Obsidian Graphite Canvas */
  --color-forge-panel: #111827;        /* Sidebar & Inspector Background */
  --color-forge-node-bg: #151d2a;      /* Node Container Body (Dark Steel) */
  --color-forge-node-header: #1e293b;  /* Node Header Accent */
  --color-forge-border: #334155;       /* Sharp Comic Border (1px / 2px) */
  --color-forge-border-hover: #f59e0b; /* Amber Border on Select/Hover */

  /* Neural Glows & Forge Fire Accents */
  --color-forge-amber: #f59e0b;        /* Active Node / Hammer Strike Trigger */
  --color-forge-orange: #fb923c;       /* Molten Loop & Route Edges */
  --color-forge-gold: #fcd34d;         /* Active Text & Glowing Pin / Handle */
  --color-forge-cyan: #38bdf8;         /* RAG LanceDB & Vector Data Stream */
  --color-forge-emerald: #10b981;      /* Checkpoint Saved & Execution Success */
  --color-forge-crimson: #ef4444;      /* Error Fallback & Guardrail Trip */
  --color-forge-yellow: #eab308;       /* Human-in-the-Loop Waiting Gate */
  
  /* Text Hierarchy */
  --color-text-primary: #f8fafc;       /* Pure Slate Light */
  --color-text-secondary: #94a3b8;     /* Muted Steel Label */
  --color-text-code: #fdba74;          /* Code & JSON Highlight */
}
```

* **Canvas Background:** Deep Obsidian Graphite (`#0b0f17`) mit dezentem Dot-Grid (`#1e293b`).
* **Node Containers:** Dark Metallic Steel (`#151d2a`) mit scharfen 1px/2px Konturen (`#334155`) und dezentem Comic-Box-Schatten.
* **Dynamische Glow- & Status-Effekte:**
  * 🟧 **Forge Amber (`#f59e0b` / `#fb923c` Pulse Glow):** Aktiver Step, laufender LLM-Call & Loop-Re-Execution.
  * 🟨 **Neural Circuit Amber (`#fcd34d` Animated Stroke):** Verbindungs-Kanten (Edges) pulsieren in Fließrichtung des Datenstroms.
  * 🟦 **Cyber Cyan (`#38bdf8`):** RAG LanceDB Retrieval, Vector Chunks & Embeddings.
  * 🟩 **Emerald Forge (`#10b981`):** Erfolgreicher Checkpoint, fertiger Output.
  * 🟥 **Molten Crimson (`#ef4444`):** Timeout, Syntax-Error oder Sicherheitsfilter-Aktivierung.
  * 🟨 **Electric Sun (`#eab308`):** Human-Gate wartet auf Freigabe.

---

## 📁 Projektstruktur (Vertical Slice Architecture — VSA)

```
Harnessforge/
├── assets/
│   ├── logo.jpg                        # 🏆 Offizielles App-Logo (Neural Forge)
│   ├── logo_option_1_comic_shield.jpg
│   ├── logo_option_2_cyber_smith.jpg
│   └── logo_option_3_neural_forge.jpg
├── backend/
│   ├── app/
│   │   ├── core/                       # Skeleton: Globale Primitives & Security
│   │   │   ├── config.py               # Host 127.0.0.1, Port, Hard-Caps
│   │   │   ├── security/               # Session-Token, Path-Sanitizer (Realpath)
│   │   │   ├── database/               # SQLite WAL-Connection
│   │   │   └── state_contract.py       # Öffentliches AgentState-Interface
│   │   ├── features/                   # Tissue: Fachliche Vertical Slices
│   │   │   ├── graph_authoring/        # .forge.json Schema, Validation, File-Explorer
│   │   │   ├── execution/              # Async Graph Interpreter, State Reducers, Loops
│   │   │   ├── providers/              # Ollama, OpenAI-kompatibel, OpenAI, OpenRouter
│   │   │   ├── retrieval/              # LanceDB Read-only RAG & Untrusted Context
│   │   │   ├── tool_execution/         # Subprocess Runner, Local Trust Mode, Config Hash
│   │   │   ├── observability/          # WebSocket Streaming, Run-Events, SQLite-Store
│   │   │   └── export/                 # Standalone agent_runner.py Generator
│   │   └── main.py                     # FastAPI App Assembly & Router-Mounts
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── architecture/               # ArchUnit / VSA Boundary Import Tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                        # Main Layout & Global Providers
│   │   ├── shared/                     # UI Primitives, Theme Tokens, Header
│   │   └── features/                   # Frontend Vertical Slices
│   │       ├── canvas/                 # FlowCanvas, Custom Nodes, Amber Edges
│   │       ├── inspector/              # Node Configuration & File Picker
│   │       ├── observability/          # Bottom Drawer, Live Trace, Token Radar
│   │       └── export_bundle/          # Export Modal & Zip Packaging
│   ├── package.json
│   └── vite.config.ts
├── templates/
│   └── standalone_runner.py.jinja      # Template für den autarken Code-Export
├── docs/
│   ├── adr/                            # Architecture Decision Records (ADR-001 bis 007)
│   └── PLAN.md                         # Implementierungsplan & CodeUltra-Gates
├── CONTEXT.md                          # Domänenvokabular & Invarianten
├── idea.md                             # Produktidee & Spezifikation
├── task.md                             # Master Implementation Task Board
└── README.md
```

---

## 🚀 Implementierungs-Fahrplan (Roadmap)

### Phase 1: Foundation & Canvas Setup
1. **Frontend Init:** Vite + React + TypeScript + Tailwind CSS + XYFlow.
2. **Custom Node Registry:** Erstellung visueller Nodes (LLM, RAG LanceDB, Loop/Condition, Tool, State Reducer, Human Gate).
3. **Backend API:** FastAPI Grundgerüst mit Local File Explorer (liest Pfade, `.md`-Dateien, LanceDB Ordner).

### Phase 2: Graph Execution Engine & WebSocket Streaming
1. **Graph Runner:** Asynchroner Interpreter, der den Frontend-Graphen ausführt.
2. **Loop-Kontrolle:** Deterministiche Evaluierung von Loop-Bedingungen (Condition Handler + Max Step Counter).
3. **Realtime Feedback:** Node-Status (Running, Done, Error) leuchtet im Canvas per WebSocket-Event auf.

### Phase 3: LanceDB RAG & File-Binding
1. **LanceDB Integration:** Nativer Tabellen-Inspector, Abfrage mit lokalen Embeddings.
2. **`agents.md` Loader:** Parsing von Markdown-Systemprompts mit Variablen-Substitution.

### Phase 4: Time-Travel Debugging & Code Export
1. **Checkpointer:** Speicherung aller Step-States in SQLite.
2. **Replay UI:** Zeitleiste im Bottom-Drawer zum Zurückspringen & Re-Run.
3. **Export Engine:** 1-Klick-Generierung von eigenständigem `agent_runner.py`.

---

*HarnessForge — Forge your autonomous agents with deterministic precision.*
