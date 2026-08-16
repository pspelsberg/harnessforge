# HarnessForge — Context und Domänenvokabular

## Zweck

Dieses Dokument definiert die Sprache, Grenzen und zentralen Invarianten von HarnessForge. Begriffe in Graphformat, UI, Runtime, Export und Tests sollen diese Definitionen verwenden.

## Produktkontext

HarnessForge ist ein lokaler Agent-Harness-Builder. Der Nutzer modelliert keine beliebige Workflow-Automation, sondern eine deterministisch begrenzte Ausführungsumgebung für LLM-gestützte Agenten: Zustand, Retrieval, Modellaufrufe, Tools und kontrollierte Zyklen werden explizit verbunden und beobachtbar gemacht.

## Begriffe

### Harness / Scaffolding
Ein **Harness** ist die deterministische Laufzeitumgebung um ein LLM: State-Schema, Prompt-Binding, Retrieval, Tool-Aufrufe, Budgets, Fehlersemantik, Validierung und Trace. **Scaffolding** bezeichnet diese kontrollierenden Strukturen, nicht das Modell selbst.

### Graph
Ein versioniertes, gerichtetes Modell aus Nodes und Edges. Der Graph besitzt exakt einen expliziten `Start`-Node und einen `Output`-Node. Standarddatenfluss erfolgt über den globalen `AgentState`; typisierte Ports werden für dedizierte Ein-/Ausgänge verwendet.

### Node
Eine validierte, benannte Operation mit Runtime-Konfiguration, Ports und UI-Position. Im MVP existieren `Start`, `LLM Call`, `RAG / LanceDB`, `Loop / Router`, `State Reducer`, `Tool` und `Output`.

### AgentState
Ein flexibles State-Dict mit validierten Standardfeldern:

```text
messages, query, retrieved_context, tool_results,
last_output, iteration, metadata
```

Custom-Keys sind erlaubt. Jede Mutation muss über einen validierten Reducer-Pfad und eine erlaubte Operation erfolgen. Der State hat eine harte Größenobergrenze.

### State Reducer
Ein deterministischer State-Mutationsschritt. Im MVP werden mindestens `SET` und `APPEND_LIST` unterstützt; weitere Operationen müssen typ- und pfadvalidiert sein. Reducer sind keine frei ausführbaren Python-Ausdrücke.

### Cycle Governance
**Cycle Governance** ist die Gesamtheit der Regeln, die Agenten-Loops deterministisch und sicher begrenzen. Zyklen sind ausschließlich über `Loop / Router` erlaubt. Jeder Loop besitzt eine deklarative Condition, True- und False-/Abschluss-Zweig, `max_iterations` und einen Pflicht-Fallback bei Limitüberschreitung. Unbegrenzte oder implizite Zyklen sind verboten.

### Loop / Router
Ein Node, der anhand einer begrenzten deklarativen Bedingung den Kontrollfluss wählt. Freie Python-Ausdrücke und LLM-Judges sind im MVP ausgeschlossen. Ein Limitüberschritt führt zwingend zum konfigurierten Fallback.

### Localhost / Single-User
Der MVP läuft als Single-User-Anwendung auf dem lokalen Rechner. Das Backend bindet nur an `127.0.0.1`; Localhost gilt trotzdem nicht als vollständige Vertrauensgrenze. Ein zufälliges Session-Token, Origin-/Host-Prüfung und restriktives CORS schützen die lokalen REST-/WebSocket-Schnittstellen.

### Workspace Boundary
Die **Workspace Boundary** ist die erlaubte Dateisystemgrenze. Pfade werden als Realpfade aufgelöst und müssen innerhalb des Workspace liegen. `..`-Traversal, Symlink-Escapes, Systempfade, `.env`, SSH-Schlüssel und vergleichbare sensible Dateien sind im MVP gesperrt. Relative Pfade im `.forge.json` sind der portable Standard.

### Local Trust Mode
Tools werden im MVP als lokale Subprozesse ausgeführt, nicht als vollständig isolierte Sandbox. Dieses Modell wird sichtbar als **Local Trust Mode** bezeichnet. Es gelten trotzdem Timeout-, Output-, Prozess-, Environment- und Workspace-Limits. Für untrusted Skripte ist eine externe OS-Sandbox wie Docker/Podman erforderlich; HarnessForge behauptet keine vollständige Isolation.

### Tool-Freigabe / `config_hash`
Ein Tool muss bewusst aktiviert werden. Die Freigabe gilt bis zur nächsten Änderung des sicherheitsrelevanten Kontexts und ist an einen `config_hash` gebunden. Der Hash umfasst mindestens Skriptpfad und Inhalt/mtime, Argumente, Environment-Allowlist, Schreibverzeichnisse und Limits. Jede Änderung invalidiert die Freigabe.

### Untrusted Context
RAG-Treffer, Tool-Outputs, externe API-Antworten und lokale Dokumentinhalte sind Daten, keine Systemanweisungen. Sie werden strukturell als `untrusted_context` markiert. Sie dürfen weder Systemprompt, Graph-Topologie, Tool-Konfiguration noch Berechtigungen überschreiben.

### Prompt Binding
Die Prompt-Zusammensetzung folgt der Priorität:

```text
globaler Prompt
→ agents.md bzw. expliziter lokaler Prompt
→ Node-spezifischer Prompt
→ dynamische State-Variablen
```

Im MVP wird nur eine sichere begrenzte Variablenersetzung unterstützt; arbitrary Jinja- oder Codeausführung ist verboten.

### Provider Adapter
Ein Provider Adapter implementiert den gemeinsamen Chat-Completion-Vertrag für einen Provider-Typ. Lokale Server, native OpenAI und OpenRouter bleiben getrennte Adaptergruppen, auch wenn sie teilweise kompatible Protokolle nutzen.

### Datenfluss-Aktivierung
Bevor ein Graph Daten an einen externen Provider senden darf, muss die Graph-/Provider-Konfiguration bewusst aktiviert werden. Änderung an Provider, Endpoint, Modell oder State-Bindings invalidiert die Aktivierung. Lokale und externe Datenflüsse werden sichtbar unterschieden.

### RAG / LanceDB
Read-only-Retrieval aus einem vorhandenen lokalen LanceDB-Ordner und einer vorhandenen Tabelle. Im MVP gibt es keine Ingestion-, Chunking- oder Embedding-Pipeline. Treffer werden normalisiert als `{text, score, metadata}` und als `untrusted_context` in den State übernommen.

### Trace / Run Event
Ein normalisiertes Ereignis eines Runs, etwa `node.running`, `node.succeeded`, `llm.token`, `rag.results`, `tool.failed` oder `run.cancelled`. Events sind größenbegrenzt, redigiert und werden per WebSocket live übertragen sowie separat in SQLite persistiert.

### Review-/Read-only-Modus
Fremde oder importierte `.forge.json`-Dateien werden zunächst analysiert, aber nicht ausgeführt. Run- und Tool-Starts bleiben gesperrt, bis der Nutzer den Graph ausdrücklich aktiviert.

### Export Runner
`agent_runner.py` ist ein eigenständiger Python-Runner mit eingebetteter, zuvor validierter Graph-Topologie. Er hängt nicht vom HarnessForge-Backend ab und validiert Workspace, Provider und Limits beim Start erneut.

## Architekturvokabular

HarnessForge wird als Modular Monolith mit Vertical Slice Architecture (VSA) geplant. `core/` ist das Skeleton für globale Primitives; `features/` ist das Tissue für Use-Case-Slices:

```text
backend/app/
├── core/
└── features/
    ├── graph_authoring/
    ├── execution/
    ├── providers/
    ├── retrieval/
    ├── tool_execution/
    ├── observability/
    └── export/
```

Ein Slice importiert keine internen Implementierungsdetails eines anderen Slices. Öffentliche DTOs, Ports und Verträge sind die erlaubten Integrationsflächen. `core/` darf keine Feature-Implementierungen importieren.

## Negative Anforderungen

HarnessForge darf im MVP nicht:

- beliebige externe Provider-URLs als freie Endpoints akzeptieren;
- API-Keys in Graph, Logs, SQLite oder Exportcode speichern;
- Workspace-Grenzen, Symlink- oder Traversal-Prüfungen umgehen;
- unlimitierte Loops, States, Prompts, Tool-Prozesse oder Outputs zulassen;
- untrusted RAG-/Tool-Inhalte als Systemanweisungen ausführen;
- fremde Graphen direkt beim Import ausführen;
- Tools als vollständig sandboxed darstellen;
- `dangerouslySetInnerHTML`, ungeprüftes Markdown oder Code aus Graphdaten ausführen;
- MCP-Autodiscovery, RLM/REPL-Codeausführung, Sub-Graphs oder Time-Travel stillschweigend im MVP aktivieren;
- bei Exportfehlern nicht unterstützte Nodes stillschweigend überspringen.

## Phase-2-Begriffe

Human-Gate, Sub-Graph, MCP-Gateway, Progressive Disclosure, Guardrail-Node, Time-Travel und RLM/REPL-Isolation sind bewusst auf Phase 2 verschoben. Ihre späteren Implementierungen benötigen eigene Verträge, Context Firewalls, Auditierung und erneute Security-/Compliance-Entscheidungen.
