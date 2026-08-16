# HarnessForge — Erweiterungen Task Board (Phase 2)

> **Planungsdokument, keine Implementierung.**
> Dieses Dokument leitet aus [`Erweiterungen.md`](Erweiterungen.md) eine umsetzbare Architektur- und Task-Roadmap ab.
> Jede Erweiterung wird als Vertical Slice (VSA) geplant und erst nach dem beschriebenen Test-/Review-Gate als abgeschlossen markiert.

## Ziel und Leitplanken

HarnessForge bleibt ein **lokaler Modular Monolith**. Die Phase-2-Erweiterungen erweitern den MVP, umgehen aber keine bestehenden Sicherheitsinvarianten. Insbesondere gelten weiterhin: WorkspaceBoundary, Local Trust Mode, Provider-Allowlist, Datenfluss-Aktivierung, State-/Budget-Caps, Redaction-by-default und explizite Graph-Aktivierung.

### Nicht-Ziele dieser Planung

- Keine stillschweigende Aktivierung von RLM, REPL, MCP, Sub-Graphs oder Time-Travel im MVP.
- Keine Behauptung einer vollständigen OS-Sandbox für lokale Subprozesse.
- Keine automatische Veröffentlichung, kein `git push` und keine dauerhafte Prompt-/Graph-Änderung ohne explizite Freigabe.
- Keine hart codierten Modellnamen oder Annahmen über zukünftige Frontier-Modelle; Provider werden über Fähigkeiten und Verträge ausgewählt.

## Definition of Done für jeden Phase-2-Slice

Ein Slice ist erst abgeschlossen, wenn alle Punkte erfüllt sind:

1. Backend-Code liegt ausschließlich im eigenen `backend/app/features/<slice>/`-Slice; Frontend-Code entsprechend in `frontend/src/features/<slice>/`.
2. Keine privaten Cross-Slice-Imports. Integration erfolgt ausschließlich über öffentliche DTOs, Ports, Events oder klar benannte Adapter.
3. Eingaben sind strikt typisiert und an der Boundary validiert; Zustands-, Zeit-, Größen-, Rekursions- und Parallelitätslimits sind fail-closed.
4. Deterministische Pytest-Unit-/Integration-/Security-Regressionen sind vorhanden.
5. Der Slice-eigene **Vitest-Lauf** ist grün.
6. Danach erfolgt ein **CodeUltra Full-Tier-Review** nach Contract v4.5: initiales Review → alle Findings beheben → erneuter Review. Erst ein Review mit `findings: []` erlaubt den nächsten Slice.
7. Backend-Gesamttests, Frontend-Gesamttests, Build und Architektur-Fitness bleiben grün.
8. Keine Secrets, Tokens, unredigierten PII, Stacktraces oder untrusted Instructions gelangen in Logs, Events, Checkpoints, Diffs oder Exporte.

## Zielarchitektur (VSA)

### Backend-Slices

```text
backend/app/
├── core/                         # nur globale Primitive, Caps, Security, Events/Ports
└── features/
    ├── graph_authoring/          # bestehender MVP-Slice
    ├── execution/               # bestehender MVP-Slice
    ├── providers/                # bestehender MVP-Slice
    ├── retrieval/                # bestehender MVP-Slice
    ├── tool_execution/           # bestehender MVP-Slice
    ├── observability/            # bestehender MVP-Slice
    ├── export/                   # bestehender MVP-Slice
    ├── repl_sandbox/             # isolierte, begrenzte Codeausführung
    ├── rlm/                      # rekursive Sub-Agenten und Context Firewalls
    ├── mcp_gateway/              # explizite MCP-Registry, Governance und Proxy
    ├── human_gates/              # persistente Approval-Handshakes
    ├── time_travel/              # immutable Checkpoints und State-Forks
    ├── continual_refiner/        # Trajectory-Auswertung und Diff-Vorschläge
    ├── coding_harness/           # deklarative Coding-Workflow-Vorlagen
    └── workspace_indexer/        # inkrementeller, lokaler Code-/Symbolindex
```

`workspace_indexer` wird als eigener Slice ergänzt, weil Indexierung, Watcher, Debouncing und LanceDB-Schreibzugriff nicht in `retrieval/` gehören. `coding_harness` konsumiert dessen öffentliche Query-Schnittstelle, importiert aber keine privaten Indexer-Implementierungen.

### Frontend-Slices

```text
frontend/src/features/
├── repl_sandbox/
├── rlm/
├── mcp_gateway/
├── human_gates/
├── time_travel/
├── continual_refiner/
├── coding_harness/
└── workspace_indexer/
```

Jeder Frontend-Slice besitzt eigene API-/WS-Clients, Zustand-State, Komponenten und Vitest-Tests. Gemeinsame Darstellung primitives (Events, Status, Fehler) gehören in `frontend/src/shared/`, nicht in einen anderen Feature-Slice.

### Erlaubte Integrationsflächen

- **Public contracts:** versionierte Pydantic-/TypeScript-DTOs des anbietenden Slices.
- **Ports:** kleine, capability-basierte Protokolle für Provider, Workspace, Execution, Events und Approval.
- **Events:** normalisierte, redigierte Events über den bestehenden EventBroker; keine direkten DB-Zugriffe eines fremden Slices.
- **Persistence:** jeder Slice besitzt eigene Tabellen bzw. einen klar abgegrenzten Namespace und greift auf RunStore nur über dessen öffentliche Methoden zu.
- `core/` darf keine Feature-Implementierung importieren. Feature-Code darf keine privaten Module eines anderen Features importieren.

### Geplante Phase-2-Verträge

Vor den fachlichen Slices wird ein kleiner Contract-Schritt geplant (noch kein Feature-Code):

- `ExtensionPolicy`: globale Caps für Tiefe, Kind-Agenten, REPL-Laufzeit, MCP-Schema-/Toolgröße, Fork-Anzahl und Approval-TTL.
- `CapabilityDescriptor`: deklarative Fähigkeiten statt Modell-/Toolnamen.
- `ContextEnvelope`: Inhalt, Herkunft, Vertrauensklasse, erlaubte Bindings und Größenbudget.
- `ApprovalRequest` / `ApprovalDecision`: nonce-, fingerprint-, run- und expires-at-gebundene Freigabe.
- `CheckpointRef` / `ForkRef`: unveränderliche Referenzen, Parent-Run und Schema-Version.
- `ExtensionEvent`: typisierte, redigierte Event-Hülle mit Extension-Namespace.

Diese Verträge sind nur gemeinsame Primitive und keine Orchestrierungslogik. Jede Erweiterung validiert zusätzlich ihre eigenen DTOs.

## Abhängigkeiten und Reihenfolge

```text
P2.0 Extension Contracts & Governance
  ├── P2.1 REPL Sandbox
  │     └── P2.2 RLM / Context Firewall
  ├── P2.3 MCP Gateway
  ├── P2.4 Human-in-the-Loop Gates
  │     ├── P2.5 Time-Travel & State Forking
  │     └── P2.6 Continual Refiner
  └── P2.7 Workspace Indexer
        └── P2.8 Coding Harnesses

P2.9 Cross-slice Security, E2E und Release-Gate
```

Die Reihenfolge ist verbindlich: keine RLM-Implementierung vor einer verifizierten Ausführungsisolation, keine Coding-Harnesses vor HITL und Tool-Governance, keine Refiner-Automation vor redigierten Checkpoints und Rollback.

---

# P2.0 — Extension Contracts & Governance Slice

## Architektur

- Versionierte Protocol-DTOs in `core/contracts` oder einem gleichwertigen globalen Contract-Bereich.
- Central `ExtensionPolicy` liest nur sichere, lokale Konfiguration; keine Erweiterung darf Caps selbst überschreiben.
- Gemeinsame Funktionen: Budgetverbrauch, Correlation-/Run-ID, Herkunft (`trusted`/`untrusted`), Redaction und Capability-Checks.
- Kein generischer „execute extension“-Dispatcher: jede Fähigkeit erhält einen expliziten Port.

## Tasks

- [x] Caps und harte Obergrenzen für alle Phase-2-Ressourcen definieren und dokumentieren.
- [x] DTOs mit strict Pydantic/TypeScript-Schemas und Schema-Versionierung entwerfen.
- [x] Event-Namespace, Fehlercodes, Cancellation- und Limit-Semantik festlegen.
- [x] Persistenz-/Retention-Regeln für neue Tabellen und Migrationen planen.
- [x] Architektur-Fitness-Regeln für neue Slices ergänzen.
- [x] Threat Model für private Daten + untrusted content + externe Kommunikation aktualisieren (Lethal-Trifecta).

## Gate

- [x] Contract-/Schema-Pytests und Frontend-Typ-/Vitest-Tests grün.
- [x] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.1 — Persistente Python-REPL / `repl_sandbox` Slice

## Fachlicher Schnitt

Ein `REPL`-Node erhält begrenzte, typisierte State-Eingaben und liefert ausschließlich ein validiertes Ergebnisobjekt zurück. Der Kernel ist nicht der HarnessForge-Prozess und erhält standardmäßig weder Netzwerk noch unbeschränkten Dateisystemzugriff.

## Backend-Plan

```text
features/repl_sandbox/
├── api.py              # Start/interrupt/status, authentifiziert
├── contracts.py        # REPLRequest, REPLResult, SandboxProfile
├── policy.py           # Allowlist, Caps, dataflow policy
├── runner.py           # Pyodide/WASM primär; isolierter Fallback nur explizit
├── sessions.py         # kurzlebige Session-/Kernel-Referenzen
├── redaction.py        # Ergebnis-/Fehlerredaction
└── events.py           # repl.started/output/failed/limited
```

- Primärziel: WASM/Pyodide mit read-only Input-Snapshot und allowlisteten Bibliotheken.
- Ein Subprozess-Fallback darf nicht als Sandbox vermarktet werden und braucht eigene Local-Trust-Freigabe; ohne verifizierte Isolation bleibt er deaktiviert.
- Persistente Sessions haben TTL, Idle-Timeout, maximalen Speicher, maximalen Output, maximalen Codeumfang und maximale Zellenanzahl.
- Schreibzugriffe sind nur über explizite Workspace-Ports und atomare, boundary-validierte Artefakte erlaubt.
- Die erste Implementierung verwendet ausschließlich den expliziten `local_trust`-Subprozess-Backend; eine WASM/Pyodide-Aktivierung bleibt bis zu einem verifizierten Runtime-Adapter deaktiviert.

## Frontend-Plan

- `REPLNode`, Code-Editor, Sessionstatus, Run/Interrupt und begrenzte Ergebnisansicht.
- Keine Ausführung beim Import eines Graphen; Code und Outputs werden als untrusted bzw. secret-redacted dargestellt.

## Security-/Test-Tasks

- [x] Netzwerk-, Subprocess-, Import-, Reflection- und Dunder-Zugriffe deterministisch sperren.
- [x] CPU-, Memory-, Wall-clock-, Input-, Output- und Session-Caps testen.
- [x] Workspace-/Symlink-/`.env`-Tests ergänzen.
- [x] Cancellation räumt Kernel und Kindprozesse sicher auf.
- [x] Vitest: Editor, Caps, Interrupt, Fehler-/Redaction-UI und Import-Read-only.
- [x] CodeUltra Full Review → Findings beheben → Review ohne Befund.

---

# P2.2 — RLM / Programmatische Sub-Agenten Slice

## Fachlicher Schnitt

Ein RLM-Node spawnt nur deklarativ konfigurierte Kind-Agenten über einen `SubAgentPort`. Kein vom LLM erzeugter String darf direkt als Python- oder Tool-Code ausgeführt werden.

## Backend-Plan

```text
features/rlm/
├── api.py
├── contracts.py        # ChildAgentSpec, ContextEnvelope, AggregateResult
├── planner.py          # deklarative Spawn-Entscheidung und Capability-Check
├── spawner.py          # depth/children/budget governance
├── firewall.py         # input/output context firewall
├── aggregator.py       # schema-validierte, begrenzte Ergebnisse
├── policies.py
└── events.py
```

- `max_depth` (Default 3), Kind-Agentenanzahl, Gesamtbudget, Wall-clock und Output-Caps werden vor Spawn reserviert und nach jedem Schritt geprüft.
- Jeder Kind-Agent erhält ein eigenes Context-Fenster, nur erlaubte Bindings und eine eindeutige Herkunft.
- Rückgabe ist ein minimiertes, schema-validiertes Aggregat; Rohkontext bleibt außerhalb des Elternprompts.
- Parent cancellation propagiert an alle Kinder; verwaiste Kinder werden erkannt und beendet.
- Providerwahl erfolgt über `CapabilityDescriptor`; externe Datenflüsse brauchen die bestehende Aktivierung und Approval-Fingerprint.

## Frontend-Plan

- RLM-Node-Inspector für Tiefe, Parallelität, Context-Bindings, Aggregation und Budget.
- Live-Ansicht der Child-Runs mit redigierten Status-/Trace-Events, nicht mit geheimem Vollprompt.

## Security-/Test-Tasks

- [ ] Prompt-Injection in Child-Context, Context-Leakage und Parent-Policy-Override regressionssicher testen.
- [ ] Rekursion, Fan-out, Cascading Failure, Retry-Storm und Token-/Kostenlimits testen.
- [ ] Falsche Child-Result-Schemas, unbekannte Bindings und Cross-run-Zugriff ablehnen.
- [ ] Vitest: Node-Config, Budgetanzeige, Child-Lifecycle und sichere Ergebnisdarstellung.
- [ ] CodeUltra Review → Fix → erneutes Review ohne Findings.

---

# P2.3 — MCP Gateway & Autodiscovery Slice

## Sicherheitsentscheidung

MCP-Autodiscovery ist **nicht** „alle lokalen Server automatisch vertrauen“. Discovery wird explizit aktiviert, auf erlaubte Transportarten/Commands/Endpoints begrenzt und erzeugt zunächst nur einen Review-/Catalog-Eintrag. Tool-Aufrufe bleiben bis zur Freigabe blockiert.

## Backend-Plan

```text
features/mcp_gateway/
├── api.py
├── contracts.py        # ServerManifest, ToolDescriptor, ResourceDescriptor
├── registry.py         # explizite, persistente Allowlist
├── discovery.py        # bounded local discovery
├── transports.py       # stdio/SSE/HTTP mit fixed validation
├── schema_filter.py    # Progressive Disclosure und Schema-Caps
├── proxy.py            # validierter Tool-/Resource-Aufruf
├── approval.py
└── events.py
```

- Servermanifest bindet Command/Hash, Workspace, Transport, Endpoint und erlaubte Capabilities.
- Keine freien URLs: SSRF-/TLS-/Host-/Port-Regeln wiederverwenden. Stdio-Commands brauchen Hash-Approval und Local Trust.
- Tool- und Resource-Schemas werden gekürzt/klassifiziert; geheime Beschreibungen und unnötige Felder werden nicht an das LLM weitergegeben.
- MCP-Responses gelten als untrusted context und werden vor Prompt-Bindings redigiert/markiert.
- Resource-/Tool-Aufrufe bekommen Timeout, Response-Cap, Rate-Limit, Cancellation und Audit-Event.

## Frontend-Plan

- Server-Catalog mit Herkunft, Transport, Hash, Capabilities und Freigabestatus.
- Tool-Schema-Review und explizite Enable-/Disable-Aktion; keine stille Canvas-Erweiterung.

## Security-/Test-Tasks

- [ ] Poisoned Server Manifest, Schema-Bomb, SSRF, Redirect, DNS-Rebinding und untrusted Resource testen.
- [ ] Tool-Missbrauch, Rechteausweitung, Stdio-Environment-Leak und Process-Group-Cleanup testen.
- [ ] Vitest: Catalog, Progressive Disclosure, Approval und Fehlerzustände.
- [ ] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.4 — Human-in-the-Loop Approval Gates Slice

## Fachlicher Schnitt

Ein Human Gate ist ein persistenter, deterministischer Execution-Handshake vor einer als kritisch markierten Aktion (Tool-Schreiben, Git-Operation, externe Kommunikation, MCP-Aufruf oder RLM-Spawn). Ablehnung und Ablauf sind sichere Terminalpfade.

## Backend-Plan

```text
features/human_gates/
├── api.py
├── contracts.py        # ApprovalRequest/Decision, ActionPreview
├── policy.py           # gate classes und default-deny
├── store.py            # eigener namespace / Migration
├── service.py          # create/approve/deny/expire
├── binding.py          # action fingerprint / nonce / run binding
└── events.py
```

- Approval bindet an `run_id`, Node, Action-Fingerprint, Graph-Version, Workspace-Realpath, User-Session und TTL.
- Nach jeder Parameteränderung wird ein neuer Fingerprint erzeugt; alte Approvals sind ungültig.
- Entscheidung ist idempotent und race-safe; doppelte Approvals, Replay und Entscheidungen nach Cancel/Expiry werden abgewiesen.
- UI zeigt Preview/Diff/Command, Datenfluss, Risiko und erwartete Schreibziele; die eigentliche Aktion bleibt im zuständigen Slice.
- Kein Freigabe-Bypass über WebSocket, REST, Export oder direkte Runner-Aufrufe.

## Frontend-Plan

- Modal/Drawer für Pending Approval, Diff-/Command-Preview, Freigeben, Ablehnen, Parameteränderung und Ablauf.
- Default deny, sichtbare Local-Trust-/External-Dataflow-Badges und sichere Fehlerdarstellung.

## Security-/Test-Tasks

- [ ] Replay, TOCTOU, stale fingerprint, concurrent decisions, cancellation und expiry testen.
- [ ] Approval-Events und UI dürfen keine Secrets/kompletten Prompts ausgeben.
- [ ] Vitest: Modal, keyboard/focus behavior, deny default, optimistic-race handling.
- [ ] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.5 — Time-Travel Debugger & State Forking Slice

## Fachlicher Schnitt

Time-Travel liest immutable, redigierte Run-Checkpoints und erzeugt einen neuen Fork-Run. Der ursprüngliche Run und seine Events werden nie mutiert.

## Backend-Plan

```text
features/time_travel/
├── api.py
├── contracts.py        # CheckpointView, ForkRequest, ForkLineage
├── reader.py           # read-only checkpoint projection
├── forker.py           # schema-/budget-validierter new run
├── lineage.py
└── events.py
```

- Fork akzeptiert nur bekannte Checkpoint-IDs, Graph-Hash und Schema-Version.
- State wird erneut durch AgentState/Reducer-/Workspace-/Approval-Validierung geführt; kein beliebiges JSON-Patching.
- Externe Provider-/Tool-/MCP-Aktionen werden im Fork standardmäßig simuliert oder verlangen neue Approval; alte Approvals werden nicht übernommen.
- Fork-Anzahl, Tiefe, Stategröße, Retention und PII-Redaction sind begrenzt.
- SQLite-Migration erhält Parent-/Fork-Beziehungen und unveränderliche Auditdaten.

## Frontend-Plan

- Zeitachse/Node-Step-Ansicht, State Inspector (read-only), kontrollierte Edit- und Fork-Aktion.
- Klare Kennzeichnung von Original, Fork, simulierten und erneut ausgeführten Aktionen.

## Security-/Test-Tasks

- [ ] IDOR auf Checkpoints/Forks, State-Poisoning, stale graph, cross-workspace und approval reuse testen.
- [ ] Vitest: Timeline, state diff, fork confirmation und lineage.
- [ ] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.6 — Continual Refiner / Self-Refinement Slice

## Fachlicher Schnitt

Der Refiner erzeugt ausschließlich erklärbare, redigierte Vorschläge. Er verändert Graph, `agents.md`, Policies oder Prompts niemals automatisch.

## Backend-Plan

```text
features/continual_refiner/
├── api.py
├── contracts.py        # Trajectory, Finding, Suggestion, Patch
├── analyzer.py         # deterministische Metriken zuerst
├── proposer.py         # Provider-Aufruf mit untrusted trajectory
├── patch_policy.py     # erlaubte Dateien/Zeilen/Operationen
├── review_store.py
├── rollback.py
└── events.py
```

- Input ist eine redigierte Projection aus Observability, nie rohe SQLite-/Secret-Daten.
- Analyse trennt Fakten, Hypothesen und LLM-Vorschläge; jede Suggestion besitzt Evidenz, Risiko, Diff und Ablaufzeit.
- Patches dürfen nur erlaubte Workspace-Dateien betreffen, werden vor Anzeige geparst und atomar angewendet; vor Anwendung muss ein HITL-Gate bestehen.
- Rollback referenziert einen vorherigen Hash/Backup und validiert erneut Graph-/Prompt-Schema.
- Keine Selbständerung des Refiners, keine automatische Änderung von Sicherheits-Policies.

## Frontend-Plan

- Findings-/Suggestion-Inbox mit Evidenz, Diff, Risiko, Apply/Reject/Rollback und Status.
- Untrusted LLM-Text wird sicher als Text dargestellt; keine HTML-/Code-Ausführung.

## Security-/Test-Tasks

- [ ] Trajectory prompt injection, secret leakage, arbitrary patch path, patch bomb und rollback race testen.
- [ ] Vitest: Diff viewer, approval requirement, rollback and redaction.
- [ ] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.7 — Workspace Indexer & Codebase Semantic Indexer Slice

## Fachlicher Schnitt

Der Indexer beobachtet ausschließlich die Workspace Boundary und schreibt in einen eigenen, versionierten lokalen Index. Retrieval bleibt read-only und erhält nur die öffentliche Query-Projektion.

## Backend-Plan

```text
features/workspace_indexer/
├── api.py
├── contracts.py        # IndexJob, FileRecord, SymbolRecord
├── scanner.py          # boundary-safe initial scan
├── watcher.py          # bounded debounce/change queue
├── parser.py           # allowlisted text/symbol parsers
├── writer.py           # atomic LanceDB/index updates
├── retention.py
└── events.py
```

- `.git`, `.env`, SSH, Symlinks, Binärdateien und Dateien außerhalb der Boundary werden ausgeschlossen.
- Dateiinhalt, Größe, MIME, Hash, mtime und Parserfehler sind begrenzt; keine unbegrenzte Queue.
- Index-Rebuild ist atomar/versioniert; fehlerhafte Teilupdates werden nicht sichtbar.
- Indexdaten gelten als untrusted context und werden beim Retrieval markiert.

## Frontend-/Test-Tasks

- [ ] Indexstatus, Queue, letzte Synchronisierung, Fehler und Pause/Resume anzeigen.
- [ ] Vitest für Status, Debounce, Exclude-Regeln und Fehlerzustände schreiben.
- [ ] Symlink-/Traversal-/Binary-/Large-file-/rapid-change-Regressionen ergänzen.
- [ ] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.8 — „Claude Code in a Box“ / Coding Harness Slice

## Fachlicher Schnitt

Coding Harnesses sind versionierte, deklarative Graphvorlagen. Sie erweitern nicht die Tool- oder Execution-Rechte; jeder Lauf verwendet die bestehenden Tool-, Workspace-, Budget- und HITL-Verträge.

```text
features/coding_harness/
├── api.py
├── contracts.py        # HarnessTemplate, StepPolicy, RunPlan
├── catalog.py
├── validator.py
├── planner.py
├── git_policy.py       # erlaubte, standardmäßig lokale Git-Aktionen
├── artifact_policy.py
└── events.py
```

- Self-healing loop: Änderung → Test → redigierte Analyse → nächster Versuch; maximale Versuche und Diffgröße sind fest.
- Tool-Ausgaben sind untrusted; `stderr` darf keine System-/Graph-/Approval-Policy überschreiben.
- `git commit` und besonders `git push` sind getrennte Capabilitys; Push ist standardmäßig deaktiviert und immer HITL-pflichtig.
- Templates werden signiert/hash-validiert, importiert zunächst read-only und dürfen keine versteckten Nodes/Rechte enthalten.
- Erfolgreiche Artefakte werden als Diff/Report ausgegeben, nicht automatisch veröffentlicht.

## Frontend-/Test-Tasks

- [ ] Template-Katalog, Preview, Capability-Anzeige und Aktivierung implementieren.
- [ ] Run-Plan, Versuchszähler, Teststatus, Diff und Gate-Status visualisieren.
- [ ] Vitest für importierte Templates, Run-Loop, Diff und Push-Gate schreiben.
- [ ] Prompt-Injection, Tool-Missbrauch, infinite repair loop, unsafe git args und secret leakage testen.
- [ ] CodeUltra Review → Fix → erneutes CodeUltra Review ohne Findings.

---

# P2.9 — Cross-Slice Release- und E2E-Slice

## End-to-End-Szenario

1. Graph importieren oder im Canvas erstellen: RLM/REPL nur nach Aktivierung.
2. Workspace-Indexer erstellt einen begrenzten Index.
3. Coding Harness plant eine Änderung und stoppt vor Tool/Git-Aktionen am Human Gate.
4. Nutzer prüft Preview und gibt nur den gewünschten Schritt frei.
5. Run produziert redigierte Checkpoints; Time-Travel erzeugt einen Fork ohne Approval-Reuse.
6. Refiner erstellt einen Diff-Vorschlag; Nutzer verwirft oder übernimmt ihn nach erneuter Validierung.
7. MCP-Catalog bleibt auf explizit erlaubten Servern und zeigt Tool-Capabilities.

## Release-Tasks

- [ ] Alle Phase-2-Schemas, Migrationen und Backward-Compatibility-Regeln dokumentieren.
- [ ] Backend Unit-/Integration-/Security-Suite vollständig grün.
- [ ] Pro Slice eigener Vitest-Lauf vollständig grün.
- [ ] Pro Slice initiales CodeUltra-Review, Fixrunde und befundfreies Finalreview dokumentiert.
- [ ] Full E2E mit Cancellation, Expiry, Fork, Rollback, MCP-Deny, RLM-Depth-Cap und REPL-Limit.
- [ ] Dependency-/SBOM-/Supply-Chain-Review und Release-Audit aktualisieren.
- [ ] `CONTEXT.md`, API-Dokumentation und Threat Model aktualisieren.
- [ ] Kein Phase-2-Feature wird implizit im MVP aktiviert.

## Abschlusskriterien

- [ ] Kein offener CodeUltra-Befund (Schema 3.2).
- [ ] Keine offenen Task-Checkboxen.
- [ ] Workspace-, Secret-, SSRF-, DoS-, Prompt-Injection-, Tool-Misuse- und Approval-Regressionen grün.
- [ ] Frontend Build und Backend-/Frontend-Gesamttests grün.
- [ ] Rollback auf MVP-Verhalten ist dokumentiert und getestet.

---

## Slice-Review-Protokoll (bei der späteren Umsetzung ausfüllen)

| Slice | Vitest | Backend/Security | CodeUltra Initial | Findings behoben | CodeUltra Final | Status |
|---|---:|---:|---|---|---|---|
| P2.0 Contracts | — | — | ausstehend | — | ausstehend | geplant |
| P2.1 REPL Sandbox | — | — | ausstehend | — | ausstehend | geplant |
| P2.2 RLM | — | — | ausstehend | — | ausstehend | geplant |
| P2.3 MCP Gateway | — | — | ausstehend | — | ausstehend | geplant |
| P2.4 Human Gates | — | — | ausstehend | — | ausstehend | geplant |
| P2.5 Time Travel | — | — | ausstehend | — | ausstehend | geplant |
| P2.6 Continual Refiner | — | — | ausstehend | — | ausstehend | geplant |
| P2.7 Workspace Indexer | — | — | ausstehend | — | ausstehend | geplant |
| P2.8 Coding Harness | — | — | ausstehend | — | ausstehend | geplant |
| P2.9 Release/E2E | — | — | ausstehend | — | ausstehend | geplant |

**Wichtig:** Alle Checkboxen in diesem Dokument beschreiben geplante Arbeit. Dieses Dokument nimmt keine Implementierung vor.
