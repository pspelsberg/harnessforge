# ADR-001: Modular Monolith mit Vertical Slice Architecture

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

HarnessForge wird als Modular Monolith mit Vertical Slice Architecture (VSA) geplant. Das Backend besitzt ein kleines `core/`-Skeleton und fachliche `features/`-Slices:

```text
backend/app/core/
backend/app/features/
  graph_authoring/
  execution/
  providers/
  retrieval/
  tool_execution/
  observability/
  export/
```

Ein Slice darf keine internen Implementierungsdetails eines anderen Slices importieren. Öffentliche DTOs, Ports und Verträge sind die erlaubten Integrationsflächen. `core/` darf keine Feature-Implementierungen importieren. Der exportierte Runner bleibt von FastAPI, React und dem Backend unabhängig.

## Begründung

- Ein lokaler Single-User-MVP benötigt keine verteilten Services.
- VSA hält Use-Case-Grenzen sichtbar und verhindert technische Layer-Kopplung.
- Ein Modular Monolith reduziert Betriebs- und Netzwerkkomplexität.
- Architektur-Fitness-Tests machen Grenzen dauerhaft überprüfbar.

## Konsequenzen

- Geringe Duplizierung zwischen Slices ist akzeptabler als enge Kopplung.
- Jede neue Cross-Slice-Abhängigkeit benötigt eine öffentliche Vertragsentscheidung.
- Importregeln laufen automatisiert in Tests/CI.
- Jeder gefundene Drift erzeugt eine dauerhafte Fitness-Regression (Ratchet-Prinzip).

## Nicht entschieden / Phase 2

Eine Aufteilung in Services erfolgt nur bei nachgewiesenen Skalierungs- oder Isolationsanforderungen. MCP-Gateways und weitere Prozesse sind kein Grund, den MVP als verteilten Monolithen zu bauen.
