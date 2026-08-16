# 🚀 HarnessForge — Zukünftige Erweiterungen & Phase-2-Roadmap (`Erweiterungen.md`)

> **Dokumentationszweck:** Dieses Dokument hält alle geplanten fortgeschrittenen Erweiterungen fest, die nach Abschluss des MVP-Basissystems (Phase 0–8 in [`task.md`](task.md)) umgesetzt werden.

---

## 1. 🧠 RLM (Recursive Language Models) & Programmatische Sub-Agenten

Inspiriert von **Prime Agent** ([PrimeIntellect-ai/prime-agent](https://github.com/PrimeIntellect-ai/prime-agent)) wird HarnessForge um rekursive Agenten-Muster erweitert.

### Kernkonzept:
* **Prompt-as-a-Variable:** Der Kontext ist kein statisches Chatfenster, sondern liegt als typisierte Variablen im State. Das LLM kann Daten programmatisch filtern und manipulieren.
* **Programmatische Sub-Agenten (`rlm(...)`):** Ein Node kann dynamisch Kind-Agenten spawnen:
  ```python
  sub_result = await rlm(
      prompt="Analysiere Modul authentication.py auf Security-Gaps",
      context={"file_content": auth_code},
      max_iterations=3
  )
  ```
* **Context Firewalls:** Kind-Agenten laufen in isolierten Kontext-Fenstern und geben nur aggregierte Ergebnisse an den Hauptgraphen zurück (verhindert Context-Rot und Token-Überlauf).
* **Rekursions-Hard-Cap:** Striktes Limit (z. B. `max_depth = 3`) verhindert Endlos-Kaskaden.

### 🤖 Kompatibilität mit Next-Gen Frontier- & Standard-LLMs (Keine Spezialmodelle nötig!):

HarnessForge ist durch seinen flexiblen Adaptervertrag und OpenRouter-Support für alle aktuellen und kommenden Frontier-Modelle vorbereitet:

* **Anthropic Tier:**
  * **Claude Sonnet 5 & Claude Opus 5** — Höchste Code- und Reasoning-Präzision für komplexe Refactorings.
  * **Claude Fable 5** — Spezialisiert auf kreative, narrative und generative Modellierung.
  * **Claude 3.7 Sonnet** — Führend in Hybrid-Reasoning und Agentic Coding.
* **OpenAI Frontier Tier (Nativ & via OpenRouter):**
  * **GPT-5.6 Luna** — Spezialisiert auf autonome Agenten-Steuerung, tiefe ReAct-Loops und RLM.
  * **GPT-5.6 Terra** — Riesen-Kontextfenster und High-Throughput Systemarchitektur.
  * **GPT-5.6 Sol** — Ultra-schnelle Ausführung mit minimaler Latenz für Worker-Subagenten.
  * **GPT-4o / o3-mini** — Bewährte Standard-Engines.
* **Google DeepMind Tier:**
  * **Gemini 3.7 Flash** — Hybrid-Thinking mit rasanter Token-Geschwindigkeit, ideal für RLM-REPL-Subcalls.
  * **Gemini 3.7 Pro** — Multimodale und tiefgehende Codebase-Analysen.
* **Lokale Open-Source-Modelle (Ollama / vLLM / LM Studio — 100 % lokal & kostenlos):**
  * **DeepSeek-R1 & DeepSeek-V3** — Open-Weights Reasoning auf Spitzen-Niveau.
  * **Qwen 2.5 Coder (7B, 14B, 32B)** & kommende **Qwen 3** Generation — Exzellente Python-REPL-Code-Generierung.
  * **Llama 3.3 (70B) & Llama 4** — Robuste lokale Allrounder.
* **Hybrid Model Mixing (Kosten- & Geschwindigkeits-Optimierung):**
  * **Chef-Orchestrator:** High-End-Modell (z. B. *Claude Sonnet 5*, *GPT-5.6 Luna* oder *Gemini 3.7 Flash*), das die Gesamtstrategie plant.
  * **Sub-Agenten (Worker):** Lokale *Qwen 2.5 Coder* oder *GPT-5.6 Sol*, die parallel Dateien durchsuchen, Tests ausführen und Diffs berechnen – ohne unnötige Token-Kosten!

---

## 2. 🐍 Persistente Python REPL & State Scratchpad

Ein interaktiver Python-Kernel als spezialisierter Node im Canvas:

* **Funktion:** Der Agent kann Python-Code generieren und in einer geschützten Umgebung (WASM / Pyodide / isolierter Subprozess) ausführen.
* **Use-Case:** Komplexe Datenanalysen, JSON/CSV-Transformationen, Regex-Extraktionen und Berechnungen direkt im Datenfluss.
* **Sicherheit:** Isolierte Laufzeitumgebung, beschränkte Bibliotheken, Timeout- und Speicherlimits.

---

## 3. 🔄 Continual Harness & Self-Refinement (`/refine`-Pattern)

Ein Selbstverbesserungs-System für Agenten-Konfigurationen:

* **Trajectory Evaluation:** Nach Abschluss eines Runs analysiert das Refiner-Modul die in SQLite gespeicherten Checkpoints (`.harnessforge/runs.db`).
* **Automatische Prompt-Optimierung:** Erkennt Fehlversuche in Loops und schlägt konkrete Verbesserungen für die lokale `agents.md` oder Systemanweisungen vor.
* **Diff & Rollback:** Vorschläge werden als Git-artiger Diff angezeigt und können mit einem Klick übernommen oder zurückgerollt werden.

---

## 4. 💻 "Claude Code in a Box" — Autonome Coding-Harnesses

Vorgefertigte Best-Practice-Graphen für Software-Entwicklungs-Workflows:

* **Self-Healing Test-Loop:**
  1. LLM generiert Code-Änderung.
  2. Tool-Node führt Testsuite aus (`pytest tests/`, `npm test`, `cargo test`).
  3. Bei Fehlern (Exit != 0) analysiert der Loop den `stderr`-Output und korrigiert den Code automatisch.
  4. Bei Erfolg (Exit == 0) führt ein Tool-Node automatisch `git commit` & `git push` aus.
* **Codebase Semantic Indexer:** Hintergrund-Sync zwischen Dateisystem und lokalem LanceDB-Vektorspeicher für sekundenschnelle Symbol- und Code-Suchen.

---

## 5. 🔌 MCP (Model Context Protocol) Integration & Autodiscovery

Integration des standardisierten Anthropic MCP-Protokolls:

* **MCP Server Discovery:** Erkennt automatisch lokal laufende MCP-Server (z. B. Filesystem, PostgreSQL, GitHub, Brave Search, SQLite).
* **Visuelle Tool-Nodes:** Wandelt gefundene MCP-Tools per Drag-and-Drop in sofort nutzbare Canvas-Nodes um.
* **MCP Governance Gateway:** Filtert übermäßige Tool-Schemas heraus (Progressive Disclosure) und sichert Tool-Aufrufe ab.

---

## 6. ⏳ Time-Travel Debugger & State Forking

Erweiterte visuelle Debugging-Werkzeuge im Frontend:

* **Interaktive Zeitleiste:** Klicke im Bottom-Drawer auf beliebige vergangene Schritte oder Loop-Zyklen.
* **State Inspector & Live-Editor:** Inspiziere den exakten `AgentState` zu diesem Zeitpunkt, ändere Variablen manuell im Browser und führe den Graphen ab diesem Checkpoint neu aus.
* **Branching Runs:** Erzeuge alternative Ausführungspfade ("Was wäre wenn?") zur Fehleranalyse.

---

## 7. 🛑 Human-in-the-Loop (HITL) Interactive Approval Gates

Interaktive Kontrollpunkte vor kritischen Aktionen:

* **Pause-Bedingung:** Pausiert den Graph-Lauf automatisch vor destruktiven Bash-Befehlen, Git-Pushes oder Schreiboperationen.
* **Approval Modal:** Im Browser erscheint ein Dialog mit dem geplanten Befehl/Diff und Optionen: `Freigeben`, `Ablehnen`, `Parameter manuell anpassen`.

---

## 8. 🏗️ Architektonische Einbettung in die VSA-Struktur

Alle Erweiterungen werden als saubere, entkoppelte Vertical Slices nach dem gleichen Standard wie der MVP integriert:

```text
backend/app/features/
├── rlm/                        # RLM Sub-Agent Spawner & Context Firewalls
├── repl_sandbox/               # Persistente Python/WASM REPL
├── continual_refiner/          # Checkpoint-Analyse & agents.md Optimizer
├── mcp_gateway/                # Model Context Protocol Discovery & Proxy
└── human_gates/                # Asynchrone Approval-Handshakes
```

---

*HarnessForge — Bereit für die nächste Evolutionsstufe autonomer Agenten-Systeme.*
