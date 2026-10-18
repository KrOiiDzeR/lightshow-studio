# Eine neue Version veröffentlichen

## Einmalig auf GitHub

Öffentliches Repository `KrOiiDzeR/lightshow-studio`, Standardbranch `main`.
Beschreibung: „Local Home Assistant lightshows with event packs, Dymera support and a theme-aware dashboard.“
Topics: `home-assistant`, `hacs`, `custom-integration`, `lightshow`, `zigbee2mqtt`.
Issues aktiviert lassen. Repositoryinhalt einschließlich `.github` hochladen; das Installations-ZIP allein reicht nicht.
Die Workflows benötigen keine persönlichen Tokens oder zusätzlichen Secrets. Veröffentlichungen verwenden den kurzlebigen eingebauten GitHub-Token mit Schreibrecht nur für Repositoryinhalte.

## Ohne lokale Git-Kenntnisse

1. Änderungen auf `main` einspielen.
2. `CHANGELOG.md` auf GitHub bearbeiten und einen Abschnitt wie `## 2.0.0-beta.3` ergänzen. Änderungen und Tests nennen.
3. Unter **Actions → Validate** alle Jobs prüfen. Ein grüner Lauf ersetzt keinen HA-/Hardwaretest.
4. **Actions → Publish release → Run workflow** auf Branch `main` öffnen.
5. Versionsnummer ohne `v` eingeben, z. B. `2.0.0-beta.3`, und starten.
6. Der Workflow setzt Manifest, Frontend-Versionskonstante und Ressourcenbeispiel, prüft Tests/HACS/hassfest, erstellt Commit und Tag `v2.0.0-beta.3`, ZIP plus SHA256 und veröffentlicht das GitHub-Release als Vorabversion.
7. Das Release und dessen ZIP unter **Releases** kontrollieren. In einer Testinstallation per HACS aktualisieren; Lampen, Pakete und Neustart prüfen.

Die erste vorbereitete Version ist `2.0.0-beta.2`; denselben Ablauf dafür verwenden.
Tags und veröffentlichte Dateien nicht nachträglich verschieben/ersetzen. Bei Korrekturen eine höhere Nummer verwenden.
Ein vorhandener Tag führt zum Abbruch. Scheitert nur die Veröffentlichung nach dem Tag-Push, ein Release für diesen bereits geprüften Tag über die GitHub-Oberfläche erstellen und das passende ZIP plus SHA256 anhängen.

## Versionsschema

`2.0.0-beta.2` → `2.0.0-beta.3` → `2.0.0-rc.1` → `2.0.0`.
Tag immer mit `v`, Manifest ohne `v`. Stabile Fehlerkorrektur z. B. `2.0.1`, neue kompatible Funktionen `2.1.0`.
Erst nach Laufzeit-/Hardwareprüfung eine stabile Version veröffentlichen. HACS benötigt ein veröffentlichtes Release für releasebasierte Updates; ein Tag allein genügt nicht.
HACS lädt hier den Code aus dem Release-Tag; `zip_release` ist absichtlich nicht aktiviert. Das zusätzliche Installations-ZIP ist für manuelle Installationen gedacht.

## Lokale Prüfungen

```text
python scripts/check_repository.py
python -m unittest discover -s tests -v
node --check custom_components/lightshow_studio/static/lightshow-studio.js
node tests/ui_smoke.cjs
python scripts/build_release.py
```

Nie `.storage`, HA-Konfiguration, Backups, Logs, private Geräteadressen oder Zugangsdaten hochladen.
