# ADR-002: Graph-Runtime, AgentState und Cycle Governance

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

Der Graph ist eine versionierte JSON-Struktur mit exakt einem `Start`- und einem `Output`-Node. Der globale `AgentState` ist der Standarddatenfluss; typisierte Ports dienen dedizierten strukturierten Ein-/Ausgängen.

Der State enthält validierte Standardfelder (`messages`, `query`, `retrieved_context`, `tool_results`, `last_output`, `iteration`, `metadata`) und erlaubt begrenzte Custom-Keys. Reducer-Operationen und Pfade werden strikt typ- und größenvalidiert.

Zyklen sind ausschließlich über `Loop / Router` erlaubt. Jeder Loop muss eine begrenzte deklarative Condition, True-/False- bzw. Abschlusszweig, `max_iterations` und einen Pflicht-Fallback besitzen. Bei Limitüberschreitung wird der Fallback gewählt. Freie Python-Ausdrücke und LLM-Judges gehören nicht zum MVP.

## Begründung

Explizite Einstieg-/Ausgangspunkte und Cycle Governance machen Ausführung, Validierung und Export deterministisch. Harte Limits schützen vor Loop-DoS und unbounded State/Prompt-Wachstum.

## Konsequenzen

- Fehlerhafte oder unvollständige Graphen dürfen nicht laufen oder exportiert werden.
- Ein Prozess führt im MVP nur einen Run gleichzeitig aus.
- Run-Zustände werden normalisiert (`created`, `validating`, `running`, `succeeded`, `failed`, `cancelled`, `limit_exceeded`).
- Stop beendet Subprozesse und Streams sofort.
- Graph-, State-, Prompt-, Node- und Run-Limits haben sichere Defaults und unveränderliche Hard-Caps.

## Sicherheitsanforderungen

Graph-JSON wird strikt über versionierte Schemas deserialisiert. Keine Python-Evaluation, keine Objekt-Deserialisierung und keine dynamische Änderung von Topologie oder Berechtigungen durch Modell-/Tool-Output. Fremde Graphen starten im Review-/Read-only-Modus.
