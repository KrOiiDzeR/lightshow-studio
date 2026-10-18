# Entwicklung und Freigabe

Zweig: `dev/configuration-ui`. Ausgangspunkt: lokaler beta.3-Stand `027f5cf`.
Die lokale Entwicklung bis `2.1.0-beta.5` wird in der öffentlichen Vorabversion `2.1.0-beta.6` zusammengeführt. Der Entwicklungszweig bleibt für weitere Arbeit erhalten.
Die laufende Home-Assistant-Installation wurde nicht verändert.

## Unabhängige Bereiche

`StudioHub` verwaltet einen gemeinsamen Store/MQTT-Anschluss und einen eigenen bestehenden `Studio`-Runner pro Bereich.
Jeder Runner besitzt eigene Snapshots, Programmposition, Vorschauen, Shuffle-/Wind-Timer und Tages-Stopp-Sperre.
Änderungen an einem anderen Bereich erhalten die Objektidentität des aktiven Runners; seine Rücksetzungsdaten und Timer gehen nicht verloren.
Alle Konfigurationsänderungen werden zentral serialisiert, vollständig validiert und zuerst auf den Datenträger geschrieben, bevor der Laufzeitstand ersetzt wird.
Eine über mehrere Bereiche doppelt verwendete Lichtentität wird abgelehnt. HA-Gruppen/Aliase mit indirekt denselben physischen Geräten sind davon nicht abgedeckt.

Der Datenteil wird nach dem ersten Speichern zum Schema-3-Bereichscontainer. Vorherige Schema-2-Daten werden beim Lesen ohne Schreiben als erster Bereich übernommen.
Vollständige Sicherungen enthalten alle Bereiche; MQTT-Optionen bleiben im Config Entry.

## Shuffle-Auswahl

Optionales Feld `shuffle_scenes` pro Bereich mit Paaren aus Paket-/Szenen-ID. Fehlt es, bleibt der Shuffle im gestarteten Paket erhalten; eine explizit leere Liste löst keinen Wechsel aus.
Ziele und Duplikate werden validiert. Die Dashboard-API kann die Auswahl nicht verändern. Ein Übergang über Paketgrenzen bleibt im gleichen Runner und erhält dessen Licht-Snapshots.

## Umsetzung

- Echter Config Flow und Options Flow; ein Studio-Eintrag pro HA-Instanz.
- Legacy-YAML-Import in einen UI-Eintrag; bestehender Store und Daten bleiben erhalten.
- Administratives Konfigurationspanel, der Integration über `config_panel_domain` zugeordnet, außerdem beim Gerät und im Optionen-Dialog verlinkt.
- Eigene Bedienungsansicht mit Shows und Zeitplan, automatische Modulregistrierung und Kartenwähler-Vorgabe.
- MQTT-Modi automatisch / eigene Bridge / deaktiviert, ohne YAML und ohne eigene Broker-Secrets.
- Konfigurationsexport und Wiederherstellung in der Integration; separate Bedien-API mit erlaubten Feldern.
- Optionales Wochenprogramm, geprüfte Ziele/Zeiten/Überschneidungen und Jahres-Event-Vorrang.
- Einstellungen ändern keine Lampen, solange keine Vorschau oder Show gestartet wird; neue Wochenzeiten starten deaktiviert.

## Noch erforderlicher Integrationstest

In einer separaten Home-Assistant-Testinstallation mit MQTT prüfen:

1. Frische Installation ohne YAML; Einrichtungsdialog, Konfigurationslink, Seitenleiste und Kartenwähler.
2. Automatischer Import vorhandener YAML-Einrichtung und vollständiger eigener v2-Daten; kein zweiter Studio-Eintrag.
3. MQTT deaktiviert, automatischer Prefix, verschachtelter manueller Prefix, Broker-Neustart und Änderungen der Optionen.
4. Einrichtung schließen/erneut öffnen, Integration neu laden/deaktivieren und HA neu starten.
5. Echte Show/Vorschau, Bereichstrennung und Rücksetzen nach Neuladen; keine doppelten Abonnements/Timer.
6. Mindestens zwei echte Bereiche gleichzeitig betreiben, getrennt stoppen und Rücksetzen prüfen; parallele Abläufe, Vorschauen, Zeitpläne und Neustart testen.
7. Wochenprogramm im HA-Zeitkontext, Jahres-Event-Vorrang, manueller Stopp und Wiederanlauf am nächsten Tag.
8. Offizielle hassfest-/HACS-Prüfung gegen die aktuelle HA-Version vor Veröffentlichung.

Erst nach erfolgreichem Test und Freigabe veröffentlichen. Öffentliche Betas nur über den dokumentierten Release-Workflow erstellen; den Entwicklungszweig nicht ungeprüft veröffentlichen.

Technische Grundlagen: offizielle Home-Assistant-Dokumentation zu [Config Flows](https://contributors.home-assistant.io/core/integrations/config-flow/), [Options Flows](https://contributors.home-assistant.io/core/integrations/options-flow/) und die [Panel-Registrierung](https://github.com/home-assistant/core/blob/2026.10.1/homeassistant/components/panel_custom/__init__.py).
