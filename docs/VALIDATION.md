# Prüfstatus der 2.2-Beta

81 Python-Tests, UI-Smoke-Test und interaktive Browserprüfung mit Beispieldaten bestanden. Details: [TEST-2.2.md](TEST-2.2.md). Native Konfiguration am 2.1-System geprüft; vollständige neue Hardwaretests bleiben ausstehend. Alte v2-/v2.1-Karten als Browser-Regressionsfälle geprüft. HACS/hassfest und Browserregression sind vor dem Release verpflichtend.

## Vorheriger 2.1-Prüfstand

# Prüfstatus der 2.1-Beta

62 Python-Tests bestanden. Abgedeckt sind bisherige Einstellungen, Datenübernahme, MQTT-Routing, Wochenzeiten, Zeitgrenzen, Jahres-Event-Vorrang, Überschneidungen und die erlaubten Dashboard-Änderungen.
Die Einrichtungs- und Options-Flow-Schritte sowie der Entry-Lebenszyklus laufen zusätzlich mit simulierten HA-Registries: einmalige Einrichtung, YAML-Import, Optionen, kein MQTT im deaktivierten Modus, Panel-/Modulregistrierung, dynamische Dienste nach Reload und Aufräumen.
Diese Simulation importiert die Produktionsmethoden, ersetzt jedoch keinen vollständigen Home-Assistant-Laufzeittest.

JavaScript-Syntax und UI-Smoke-Test prüfen die getrennten Ansichten, gesperrte Konfigurationsreiter im Dashboard und getrennte Speicher-API-Aufrufe.
Eine lokale Browserprüfung mit Beispieldaten prüft Navigation, Show-Start/Stopp, Speichern der Bedienoptionen, Wochenzeiten, MQTT-Eingabe, vollständigen Export, Themefarben und Mobilansicht.
Vorschaubilder und die eigenständige HTML-Vorschau liegen in diesem Ordner und enthalten ausschließlich Beispieldaten.

Repositorystruktur, JSON, Python-Syntax und die Prüfung auf typische private Dateien/Zugangsdaten werden separat geprüft.
Die offiziellen HACS- und hassfest-Actions wurden im Release-Workflow vor dem Erstellen von Tag und Release ausgeführt. Ihr konkretes Ergebnis ist am jeweiligen GitHub-Actions-Lauf ablesbar.
Reale HA-Startsequenz, neue native Konfigurationsdialoge, tatsächliche Migration und Hardwaresteuerung bleiben auf einem Testsystem zu prüfen; siehe DEVELOPMENT.md.


Zusätzliche Bereichstests verwenden die tatsächlichen Produktionsklassen mit simulierten HA-Lichtaktionen: zwei gleichzeitig laufende Shows mit unterschiedlichen Farben, isoliertes Stoppen/Rücksetzen, unabhängige Zeitpläne, erhaltene Ablaufpositionen und Snapshots beim Bearbeiten anderer Bereiche.
Geprüft sind außerdem Bereich anlegen/umbenennen/löschen, Schutz des letzten/laufenden Bereichs, doppelte Lampen, Migration ohne Schreiben beim Laden, vollständige Wiederherstellung und unveränderter Laufzeitstand bei Schreibfehlern.
Ein Fehler im Scheduler eines Bereichs blockiert die Verarbeitung anderer Bereiche nicht.
Der echte Browser testet zusätzlich die Übersicht zweier parallel laufender Demo-Shows, getrenntes Stoppen sowie Anlegen, Umbenennen und Löschen eines Testbereichs. Diese Tests verwenden ausdrücklich keine echten Lampen.

Die UI-Überarbeitung wurde zusätzlich im Browser geprüft: gestaltete Shuffle-/Wind-Schalter, Intervallvorgaben, Regler mit Speicherung von 330 Sekunden, Zustandsübernahme der Schalter, auf-/zuklappbare Abschnitte mit Erhalt des Zustands nach Neuzeichnen und Tastaturwechsel zwischen Reitern. Helle/dunkle Darstellung und 390-Pixel-Mobilansicht wurden erneut mit Beispieldaten geprüft. Screenshots: `dev-design-effects.png` und `dev-design-folders.png`.

Die Bereichserstellung wurde erneut geprüft, während `window.prompt` und `window.confirm` absichtlich Fehler werfen: eingebautes Formular öffnen, leeren Namen zurückweisen, Name/Symbol eingeben, per Enter erstellen, im Dashboard auswählen, neue Lampe zuordnen und speichern, Bereich umbenennen sowie Löschung abbrechen und bestätigen. Das Abbrechen einer neuen Bereichserstellung legt keinen Bereich an. Diese Prüfung benötigt keine automatisch bestätigten Browserdialoge mehr. Die Vorschau hält Änderungen nur für die aktuelle Sitzung.


Shuffle-Auswahl: Validierung unbekannter/doppelter Szenen, leere Auswahl ohne Rückfall, einzelner Eintrag, Vermeidung sofortiger Wiederholung und Erhalt des bisherigen Verhaltens ohne gespeicherte Auswahl geprüft.
Produktionstick mit simulierten Lampen wechselt von Halloween zu einer ausdrücklich ausgewählten Weihnachtsszene, während ein anderer Bereich unverändert weiterläuft. Feste Abläufe behalten trotz Shuffle-Auswahl ihre Schrittfolge.
Im Browser wurden Schalter aus Halloween und Ambiente gewählt, abgewählt und gespeichert; nach Bereichswechsel blieb die Auswahl erhalten und der andere Bereich unverändert. Der Dashboard-Speicherpfad kann die Auswahl nicht überschreiben. Das Entfernen einer Szene bereinigt ihre Auswahlreferenz. Mobilansicht ohne horizontalen Seitenüberlauf bestätigt.
