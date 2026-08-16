# ADR-003: Workspace Boundary und Local Trust Mode

- **Status:** Accepted
- **Datum:** 2025-02-14
- **Kontext:** HarnessForge MVP

## Entscheidung

Dateien und Tools sind standardmäßig auf den explizit gewählten Workspace begrenzt. Pfade werden als Realpfade geprüft; Traversal, Symlink-Escapes, Systempfade, `.env`, SSH-Schlüssel und vergleichbare sensible Dateien sind gesperrt. Das Zielsystem für die strenge Umsetzung ist Linux/Unix.

Tools laufen im MVP als lokale Subprozesse im sichtbaren **Local Trust Mode**. Das ist keine vollständige Sandbox. Standardmäßig sind sie read-only. Schreibzugriffe benötigen deklarierte Unterverzeichnisse innerhalb des Workspace. Timeout, stdout/stderr, Prozessgruppe, Environment und Run-Dauer sind begrenzt.

Eine Tool-Freigabe wird als `config_hash` an Skriptpfad und Inhalt/mtime, Argumente, Environment-Allowlist, Schreibverzeichnisse und Limits gebunden. Jede relevante Änderung invalidiert sie. Die Prüfung wird unmittelbar vor Ausführung wiederholt, um TOCTOU-Risiken zu reduzieren.

## Begründung

Der Workspace verhindert unkontrollierten Dateizugriff; die transparente Trust-Mode-Kennzeichnung vermeidet eine falsche Sicherheitsgarantie. Strengere Docker/Podman/WASM-Isolation ist wertvoll, gehört aber nicht in den nicht implementierten MVP-Vertrag.

## Konsequenzen

- Ein Nutzer muss Tools bewusst aktivieren.
- Fremde Graphen können keine Prozesse starten, bevor sie explizit aktiviert wurden.
- Untrusted Skripte benötigen eine externe OS-Sandbox.
- Netzwerkzugriff wird im MVP deaktiviert oder als explizite Restgefahr kenntlich gemacht.
- Security-Tests decken Traversal, Symlinks, TOCTOU, Schreibgrenzen, Timeout und Output-Caps ab.
