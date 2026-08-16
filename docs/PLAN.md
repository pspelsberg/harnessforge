# HarnessForge — Implementierungsplan

**Status:** bestätigte Planung, noch keine Implementierung  
**Planungstier:** CodeUltra Full  
**Primäre Plattform:** Linux/Unix, localhost, Single-User

## 1. Ziel und Leitplanken

Der MVP liefert einen vollständigen lokalen Flow:

```text
Graph im Canvas
→ agents.md / lokaler Prompt
→ Read-only-LanceDB-RAG
→ LLM Call und begrenzter ReAct-Loop
→ Tool-Subprozess im Local Trust Mode
→ Live-WebSocket-Trace
→ eigenständiges agent_runner.py-Bundle
```

Leitplanken:

- Modular Monolith plus VSA statt verteilter Services.
- Exakte Graph- und State-Verträge vor Runtime-Features.
- Security-by-default, sichtbare Aktivierungen und harte Caps.
- Kein Code aus Graphdaten, LLM-Outputs oder Prompt-Templates ausführen.
- Jede Fehler- oder Sicherheitskorrektur erzeugt einen dauerhaften Regressionstest.

## 2. Zielstruktur

```text
backend/app/
├── core/                              # Config, State, Security, DB-Primitives
└── features/
    ├── graph_authoring/               # Graph-Datei, Canvas-Vertrag, Validierung
    ├── execution/                     # Interpreter, State, Cycle Governance
    ├── providers/                     # Ollama, lokale OpenAI-kompatibel, OpenAI, OpenRouter
    ├── retrieval/                     # LanceDB-Inspektion und Read-only-Suche
    ├── tool_execution/                # Workspace, Local Trust Mode, Subprozesse
    ├── observability/                 # WebSocket, Events, SQLite-Runs, Retention
    └── export/                        # Validierung, Generator, Runner-Bundle
frontend/src/
├── features/                          # Canvas- und Inspector-Slices
├── shared/                            # UI-Primitives und öffentliche Verträge
└── app/
templates/
└── standalone_runner.py.jinja         # nur als geplante Exportvorlage
docs/adr/
```

VSA-Regeln werden durch automatisierte Import-/Architekturtests gesichert: `core/` importiert keine Features; Features importieren keine privaten Module anderer Features; der Export-Runner importiert weder FastAPI noch React.

## 3. Phasen und Meilensteine

### Phase 0 — Foundation, Verträge und Security Baseline

**Ergebnisse:**

- Repository-/Tooling-Entscheidungen und reproduzierbare Dependency-Strategie.
- versioniertes `.forge.json`-Schema (`schema_version: "1"`).
- AgentState-, Port-, Event-, Provider- und Export-Verträge.
- VSA-Importregeln und erste Architektur-Fitness-Tests.
- Threat Model nach STRIDE sowie CodeUltra-Kriterien-Matrix.
- Localhost-Session-Token, CORS-/Origin-/Host-Strategie als Designverträge.
- sichere Pfad- und sensible-Dateien-Policy.

**Gates:** Schema- und Boundary-Tests; keine Implementierung ohne validierte öffentliche Verträge.

### Phase 1 — Graph Authoring und Validation Slice

**Ergebnisse:**

- Canvas mit Node-Palette, Drag-and-drop, Verbindung, Löschen, Duplizieren.
- Inspector für Runtime-Konfiguration und UI-Position getrennt.
- Undo/Redo, Zoom, Pan, Fit-to-View und LocalStorage-Recovery.
- Live-, Save-, Run- und Export-Validierung.
- Errors blockieren Run/Export; Warnings blockieren Export standardmäßig; Infos sind erklärend.
- exakt ein Start- und ein Output-Node.
- Live-Markierung ungültiger Nodes und Edges.

**Gates:** Graphgrenzen, Porttypen, unerreichbare Nodes, ungültige IDs und JSON-Roundtrips sind getestet.

### Phase 2 — Execution und Cycle Governance Slice

**Ergebnisse:**

- asynchroner Interpreter für den validierten Graphen.
- AgentState und strikt validierte Reducer.
- deklarative Loop-/Router-Conditions.
- Zyklen nur über Loop-/Router-Nodes.
- max. Iterationen und Pflicht-Fallback.
- Run-Lifecycle: `created`, `validating`, `running`, `succeeded`, `failed`, `cancelled`, `limit_exceeded`.
- ein aktiver Run pro Prozess.
- sofortiges Stop-Verhalten mit Prozessgruppen-/Stream-Abbruch.

**Gates:** Property-Tests für Graphzyklen und Limits; Fake-Provider-Integration; State-/Prompt-/Run-DoS-Tests.

### Phase 3 — Provider Slice

**Ergebnisse:**

- gemeinsamer Chat-Completion-Vertrag.
- getrennte Adapter für Ollama, lokale OpenAI-kompatible Server, native OpenAI und OpenRouter.
- Streaming, Structured Output, Token-/Kostenmetadaten und normalisierte Fehler.
- erlaubte Ziele: Loopback-Allowlist, `api.openai.com/v1`, `openrouter.ai/api/v1`.
- Environment-Variable-Referenzen statt Secrets.
- externe Datenfluss-Aktivierung und sichtbare Datenübertragung.
- Timeout-, Redirect-, Response-Size- und SSRF-Prüfungen.

**Gates:** Fake-Provider, Contract-Tests, SSRF-/Redirect-/Secret-Regressionen und Provider-Config-Hash-Invalidierung.

### Phase 4 — Retrieval Slice

**Ergebnisse:**

- vorhandene LanceDB-Ordner und Tabellen read-only inspizieren.
- Text-/Vektorspalten automatisch erkennen, manuell überschreibbar.
- vector/full-text/hybrid nur entsprechend dem bestehenden Schema.
- Query aus State-Pfad, standardmäßig `query`.
- normalisierte Treffer `{text, score, metadata}`.
- begrenzte Trefferzahl und Chunkgröße.
- Ergebnisse als `untrusted_context` markieren.

**Gates:** temporäre LanceDB-Testdatenbanken, inkompatible-Schema-Tests, Datenfluss- und Prompt-Injection-Regressionen.

### Phase 5 — Tool Execution Slice

**Ergebnisse:**

- Workspace-Realpath-Grenze mit Traversal-/Symlink-/sensible-Dateien-Schutz.
- Unix-orientierte strenge Prüfung, einschließlich TOCTOU-Abwehr, soweit OS-seitig möglich.
- Local Trust Mode mit sichtbarem Warnhinweis.
- standardmäßig read-only; deklarierte Workspace-Unterverzeichnisse für Schreibzugriff.
- minimale Environment-Allowlist, kontrolliertes `PATH`, keine unkontrollierte Shell-Auswertung.
- 15-Sekunden-Default, 60-Sekunden-Hard-Cap, stdout/stderr-Caps.
- Prozessgruppe und sofortige Terminierung.
- `config_hash`-gebundene Freigabe.

**Gates:** Path Traversal, Symlink Escape, TOCTOU, Timeout, Prozessgruppen-, Output-Cap-, Secret-Vererbungs- und Schreibrechte-Tests.

### Phase 6 — Observability Slice

**Ergebnisse:**

- WebSocket-Handshake mit Session-Token und Origin-Prüfung.
- Node-Status, Iterationen, RAG-Scores, Tool-Exitcodes, LLM-Streaming und Run-Status.
- gekürzte/redigierte Events und Größenlimits.
- SQLite unter `.harnessforge/runs.db`.
- Standard-Retention 30 Tage, konfigurierbar.
- Run löschen / alle Runs löschen.
- vollständige Snapshots nur im expliziten lokalen Debug-Modus.
- Plaintext-/JSON-UI ohne ungeprüftes Markdown.

**Gates:** XSS-, Secret-Leak-, WebSocket-Schema-, Event-Size- und Retention-Tests.

### Phase 7 — Export Slice

**Ergebnisse:**

- Export-Validierung mit klaren Fehlern bei unvollständigen oder nicht unterstützten Nodes.
- Bundle mit `agent_runner.py`, exakt gepinntem `requirements.txt` und `.env.example`.
- eingebettete validierte Graph-Topologie.
- `argparse`, stdout-Streaming, JSON-Logs, Exit-Codes und `--dry-run`.
- erneute Boundary-, Provider- und Limitvalidierung im Runner.
- keine FastAPI-/React-/HarnessForge-Backend-Abhängigkeit.

**Gates:** generierten Runner isoliert ausführen; Dependency-/Supply-Chain-Prüfung; Runner-Import-Fitness; keine Secret-Leaks.

## 4. MVP-Sicherheitsmodell und CodeUltra-Gates

Die Planung folgt dem CodeUltra Full Tier und leitet Kriterien nach Komponenten-Archetyp ab. Für alle relevanten Slices werden insbesondere folgende Kriterien als Predictive Review Gates und Tests geführt:

| Bereich | CodeUltra-Kriterien | Planungsfolge |
|---|---|---|
| Eingabe/Graph/Config | C-VAL, C-INJ, C-CFG, F-INT | Pydantic-Schemas, keine freie Auswertung, sichere Defaults |
| Dateisystem/Tools | F-PATH, F-TOC, F-ASI, F-DOS | Realpath, TOCTOU, Trust Mode, Prozess-/Output-Caps |
| LLM/RAG/Provider | F-LLM, F-ASI, F-DOS, C-LOG | untrusted context, Datenfluss-Aktivierung, Limits, Redaction |
| Outbound HTTP | C-LOG, F-CRY, F-DOS, F-INT | feste Ziele, TLS für externe Ziele, Timeouts, Response-Limits |
| Deserialisierung/Export | C-VAL, F-INT, F-SC | versionierte Schemas, gepinnte Dependencies, reproduzierbare Bundles |
| VSA/Runtime | F-FIT, F-DES, F-EXC | Importregeln, deterministische Fehlerzustände, Ratchet |
| Datenschutz | C-LOG, F-CMP | Privacy-by-default, Retention/Löschung, Datenflusskennzeichnung |

Zu jedem Security-Fund gehören Schweregrad, CWE, OWASP-2025-Kriterium und im Full Tier ein CVSS-Basiswert. Kritische Pfade erhalten Regressionstests vor dem Merge.

### Lethal-Trifecta-Gegenmaßnahmen

HarnessForge kann private Workspace-Daten, untrusted Retrieval-/Tool-Inhalte und externe Kommunikation verbinden. Deshalb:

- externer Provider-Request benötigt explizite Aktivierung;
- übertragene State-Bindings sind sichtbar und änderungsgebunden;
- sensible Felder können ausgeschlossen werden;
- Retrieval/Tools bleiben untrusted data;
- kein automatisches Übertragen kompletter Workspace-Inhalte;
- lokale-only Nutzung ist ein expliziter Modus.

### Localhost- und Browser-Schutz

- `127.0.0.1`, kein `0.0.0.0` im MVP.
- zufälliges Session-Token pro Serverstart für REST und WebSocket.
- restriktives CORS, Origin-/Host-Validierung, keine Wildcard-Credentials.
- sichere Response-Header/CSP.
- React-Textdarstellung statt `dangerouslySetInnerHTML`.
- LocalStorage-Recovery ist Datenquelle für UI-Recovery, niemals alleinige Runtime-Autorisierung.

## 5. Ressourcen-Hard-Caps

Sichere Defaults sind konfigurierbar, aber niemals über die Hard-Caps hinaus:

| Ressource | MVP-Hard-Cap |
|---|---:|
| Nodes | 50 |
| Loop-Schritte | 50 |
| State-Größe | 5 MB |
| Run-Dauer | 5 Minuten |
| Tool-Timeout | 60 Sekunden (Default 15 Sekunden) |
| Tool stdout/stderr | je 50 KB als Planungsdefault |

Zusätzliche Caps für Graphdatei, Edges, Prompt, RAG-Treffer, Chunkgröße, WebSocket-Event und LLM-Stream werden vor Implementierung als feste Werte in den Verträgen dokumentiert. Graph, CLI oder Provider dürfen sie nicht unbeschränkt erhöhen.

## 6. Teststrategie und Definition of Done

### Testarten

- Backend: Pytest Unit- und Integrationstests.
- Frontend: Vitest und React Testing Library.
- Graphvalidierung: Property-/Grenzfalltests.
- Runtime: deterministische Fake-Provider und Fake-Tools.
- Retrieval: temporäre LanceDB-Testdaten.
- API: Vertragstests gegen den dokumentierten HTTP-/WebSocket-Vertrag.
- Export: isolierte Ausführung des erzeugten Bundles.
- Security: Path Traversal, Symlink, TOCTOU, SSRF, XSS, Secret-Leak, Prompt Injection, Loop-/Tool-DoS, Deserialisierung.
- Architektur: automatisierte Import-/VSA-Fitnessregeln.

### Definition of Done

Ein Slice ist erst fertig, wenn:

1. öffentliche Verträge und Fehlersemantik dokumentiert sind;
2. Unit- und Integrationstests vorhanden sind;
3. relevante CodeUltra-Predictive-Review-Gates abgedeckt sind;
4. Security- und Ressourcenlimits getestet sind;
5. Logs und Fehler keine Secrets oder unnötigen PII-Inhalte enthalten;
6. VSA-Importregeln grün sind;
7. ein Export-Slice seine Runner-Verträge ohne Backend-Abhängigkeit erfüllt;
8. jeder behobene Bug eine Regression besitzt.

MVP-Freigabe erfordert vollständig grüne Security- und Exportpfade.

## 7. Dokumentations- und Release-Artefakte

Erforderlich:

- `README.md`
- `CONTEXT.md`
- diese Datei
- ADRs 001–007
- versioniertes Graphschema
- API-/WebSocket-Vertrag
- Security-/Threat-Model und CodeUltra-Kriterien-Matrix
- Export-/Dependency-Manifest
- Release-Checkliste mit SBOM- und Dependency-Scan-Schritt

## 8. Bewusste Phase-2-Abgrenzung

MCP-Autodiscovery, MCP-Governance-Gateway, Sub-Graphs, Human-Gates, Guardrail-Node, Time-Travel und RLM/REPL-Isolation werden nicht im MVP versteckt vorbereitet oder aktiviert. Phase 2 benötigt jeweils eigene Verträge, Berechtigungsmodelle, Auditierung, Context Firewalls, Datenretention-Entscheidungen und Security-Regressionen. Besonders RLM/REPL-Ausführung darf nur mit echter Code-Sandbox und expliziten Rekursions-/Ressourcenlimits eingeführt werden.
