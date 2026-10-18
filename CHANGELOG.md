# Änderungen

## 2.1.0-beta.6

Erste öffentliche 2.1-Beta mit den zusammengeführten Verbesserungen aus der lokalen Entwicklung.

- Einrichtung über **Geräte & Dienste** mit Config Flow, Options Flow und administrativer Konfigurationsseite. Neue Installationen benötigen keine YAML-Einträge und keine manuelle Dashboard-Ressource.
- Automatischer Import bisheriger YAML-Installationen; vorhandene Lampen, Pakete, Szenen und Zeitpläne werden als erster Bereich übernommen.
- Bis zu 30 unabhängige Bereiche mit parallelen Shows, eigenen Abläufen, Zeitplänen und Rücksetzungsdaten; kompakte Übersicht und Bereichsauswahl im Dashboard.
- Konfiguration und Bedienung getrennt. Lampen, Zigbee2MQTT, Szenenbearbeitung, Shuffle-Auswahl sowie Import/Export liegen in der Integration; Start/Stopp, Shuffle-Schalter, Intervall und Zeitpläne bleiben im Dashboard.
- Eigene Shuffle-Szenenauswahl pro Bereich über alle Pakete; leere Auswahl löst keinen Wechsel aus, feste Abläufe behalten ihre Reihenfolge.
- Wochenprogramm zusätzlich zu Jahres-Events, Theme-konforme Schalterkarten, aufklappbare Funktionsgruppen und deutlichere Navigation.
- Bereiche ohne Browser-Pop-ups anlegen und löschen. Vollständige Sicherung/Wiederherstellung aller Bereiche.
- 62 lokale Python-Tests sowie Browserprüfungen mit Beispieldaten. Vollständige neue Hardware-/Migrationstests stehen noch aus; weiterhin Vorabversion.
- Voraussetzung: Home Assistant 2026.10 oder neuer. Nach dem Update HA neu starten und Browser neu laden. Vor dem ersten Speichern vollständiges Backup behalten: das neue Bereichsformat ist mit 2.0.0-beta.3 nicht rückwärtskompatibel.

## 2.1.0-beta.5 — nur lokale Entwicklung, unveröffentlicht

- Konfigurationsreiter „Shuffle“ mit Schaltern für alle Szenen aller Pakete des gewählten Bereichs.
- Feste, bereichsspezifische Shuffle-Auswahl auch über Paketgrenzen; keine sofortige Wiederholung der aktuellen Szene.
- Leere Auswahl löst keinen Wechsel aus; feste Show-Abläufe behalten ihre Reihenfolge.
- Dashboard zeigt die Anzahl ausgewählter Szenen und behält Aktivierung/Intervall. Seine Bedien-API kann die konfigurierte Auswahl nicht überschreiben.
- Vorhandene Einstellungen ohne eigene Auswahl behalten den bisherigen Shuffle im gestarteten Paket. Beim Löschen von Szenen/Paketen werden Auswahlverweise bereinigt.

## 2.1.0-beta.4 — nur lokale Entwicklung, unveröffentlicht

- Bereichserstellung als eingebautes Formular statt Browser-`prompt`, damit sie auch bei unterdrückten Browserdialogen funktioniert.
- Name und Symbol direkt eingeben, per Schaltfläche oder Eingabetaste erstellen; Fehler und Abbruch innerhalb der Oberfläche.
- Bereichslöschung ebenfalls mit eingebauter Bestätigung statt Browser-`confirm`.
- Vorschau-Test ohne verfügbare Browserdialoge: Bereich erstellen, im Dashboard auswählen, Lampe zuordnen, umbenennen, Löschen abbrechen/bestätigen und Erstellung abbrechen.

## 2.1.0-beta.3 — nur lokale Entwicklung, unveröffentlicht

- Vorhandenen Theme-Stil erhalten; Funktionen durch aufklappbare Abschnitte mit eigenen Überschriften, Symbolen und Rahmen gegliedert.
- Deutlich erkennbare Ansichtsreiter mit Kurzbeschreibung, aktiver Markierung und Tastatursteuerung.
- Shuffle und Wind als gestaltete Schalterkarten; Szenenwechselintervall mit Regler, lesbarer Dauer und Zeitvorgaben.
- Bereichsauswahl und aktuell bedienter Bereich stärker hervorgehoben; separate Gruppen im Szenen-Editor, für Zeitpläne und für Sicherungen.
- Offene/geschlossene Abschnitte bleiben beim Wechseln und Aktualisieren innerhalb der Karte erhalten.

## 2.1.0-beta.2 — nur lokale Entwicklung, unveröffentlicht

- Bis zu 30 unabhängige Bereiche mit eigenen Lampen, Paketen, Szenen, Abläufen, Shuffle-/Wind-Einstellungen und Zeitplänen.
- Parallele Shows mit eigenem Status und Rücksetzen je Bereich; Dashboard mit Bereichsauswahl und kompakter Übersicht.
- Bereiche im Konfigurationsbereich anlegen, benennen und löschen. Doppelte Lampenzuordnungen über Bereichsgrenzen werden abgelehnt.
- Vorhandene Einzelkonfiguration wird verlustfrei zum ersten Bereich; vollständiger Export/Import umfasst alle Bereiche.
- Bereichsspezifische Websocket- und Service-Aufrufe; bestehende Start-Aufrufe ohne Bereich verwenden den ersten Bereich, Stopp ohne Bereich stoppt alle.

## 2.1.0-beta.1 — nur lokale Entwicklung, unveröffentlicht

- Einrichtung über Home-Assistant-Config-Flow statt manuell erforderlicher YAML-Konfiguration.
- Integrationskonfiguration für Verbindung, Lampen, Szenen, Abläufe und Pakete; Dashboard ausschließlich für Bedienung und Zeitpläne.
- Automatische Kartenregistrierung und sofort verfügbare Bedienungsansicht.
- Individuelle Zigbee2MQTT-Einstellungen und vollständiger Konfigurationsexport/-import.
- Optionales Wochenprogramm mit Wochentagen und Zeitfenstern.
- Bestehende v2-Daten und YAML-Installationen werden übernommen; Änderungen der Bedienung können keine Lampen/Pakete überschreiben.

# Changelog

## 2.0.0-beta.3 — 2026-10-18

- Zigbee2MQTT-Bridge-Prefix automatisch aus der Geräteliste ermitteln; Groß-/Kleinschreibung erhalten.
- Native Dymera-Effekte und Tempo an das tatsächlich erkannte MQTT-Topic senden.
- Optionales `mqtt_base_topic` für verschachtelte Prefixe und die gezielte Auswahl einer Bridge.
- Gerätelisten mehrerer Bridges getrennt aktualisieren; mehrdeutige Gerätenamen beim Senden ablehnen.
- Erkannte Geräte in der Lampenansicht anzeigen und Regressionstests zur Topic-Erkennung ergänzen.

## 2.0.0-beta.2 — 2026-10-18

- Repository-Struktur für HACS mit gebündelter Dashboard-Karte.
- Transparenter Kartenhintergrund; Flächen, Texte, Formulare und Hinweise folgen dem Home-Assistant-Theme.
- Optional `background: theme`, sichtbarer Tastaturfokus und mobile Darstellung.
- Neue Installationen starten ohne vorgegebene private Lampennamen.
- Bestehender Domain-Name und Speicherformat 2 bleiben erhalten.
- Tests und manuell auslösbarer Release-Workflow mit Tag, Versionsprüfung und ZIP.

## 2.0.0-beta.1

- Ursprüngliches manuell verteiltes Beta-Paket mit Event-Paketen, Szenen, Abläufen und v1-Import.
