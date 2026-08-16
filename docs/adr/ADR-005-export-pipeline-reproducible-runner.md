# ADR-005: Export-Pipeline und reproduzierbares Runner-Bundle

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

Der Export erzeugt ein autarkes Bundle:

```text
agent_runner.py
requirements.txt
.env.example
```

`agent_runner.py` enthält die validierte Graph-Topologie, bietet `argparse`, `--dry-run`, stdout-Streaming, JSON-Logs und saubere Exit-Codes. Es importiert weder FastAPI noch React oder interne HarnessForge-Backend-Module. `requirements.txt` enthält exakt gepinnte, getestete Versionen.

Der Runner validiert beim Start erneut Workspace, Provider-Konfiguration, Secrets-Referenzen und Sicherheitslimits. CLI-Optionen dürfen Hard-Caps nicht überschreiten.

## Begründung

Ein eingebetteter Runner erfüllt das Zero-Runtime-Lock-in-Ziel und bleibt unabhängig vom lokalen Web-Backend. Exakte Pins verbessern Reproduzierbarkeit und Supply-Chain-Prüfbarkeit.

## Konsequenzen

- Unvollständige, ungültige oder nicht unterstützte Nodes blockieren den Export mit verständlichen Fehlern.
- Secrets werden nie eingebettet; `.env.example` enthält nur leere Variablennamen.
- Bundle-Tests führen den generierten Runner isoliert aus.
- Release-Prüfungen umfassen Dependency-Scan, Lock-/Pin-Integrität und SBOM.
- Graph-Datei wird zur Laufzeit nicht benötigt, sofern die Topologie vollständig eingebettet ist.
