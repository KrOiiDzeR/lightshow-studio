# Prüfstatus

Lokal bestanden: 14 Python-Tests, JavaScript-Syntax und Darstellung aller fünf Reiter im simulierten DOM; Repositorystruktur, Metadaten, JSON und Prüfung auf typische private Dateien/Zugangsdaten.
Eine zusätzliche Prüfung mit einem echten Browser und simulierten HA-Daten bestätigte helle/dunkle Darstellung, alle fünf Reiter ohne Seitenüberlauf, 390-Pixel-Mobilansicht und die Optionen transparent/theme. Vorschaubilder liegen in diesem Ordner.
Der zusätzliche Speichertest bestätigt für simulierte vorhandene v2-Daten: Laden ohne Überschreiben und ohne erneuten v1-Import. Er ersetzt keinen Test auf einem realen HA-Server.
Automatische Prüfungen decken JSON, Syntax, Einstellungen, Paketimport, v1-Migration und die Darstellung aller fünf Kartenreiter in einem simulierten DOM ab.
Der Release-Workflow führt zusätzlich die offiziellen HACS- und hassfest-Actions auf GitHub aus.

Nicht durch diese Prüfungen abgedeckt: reale HA-Startsequenz, HACS-Installation/Update, tatsächliche Zigbee2MQTT-Payloads, Firmwareverhalten, Lichtzustandswiederherstellung und bestehende produktive Daten.
Diese Punkte müssen vor einer stabilen Version in einer Testinstallation geprüft werden.
