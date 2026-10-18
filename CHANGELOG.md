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
