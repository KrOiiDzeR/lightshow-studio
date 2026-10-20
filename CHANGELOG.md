# Änderungen

## 2.3.2-beta.1

- Leere Bedien- und Konfigurationsseiten bei mehrfach geladenen Ressourcen behoben: dieselbe Frontend-Version wird nur einmal registriert. Zusätzliche Ressourcenadressen dürfen keine rekursive Weiterleitung der eigenen Kartenklasse erzeugen.
- JavaScript-Deklarationen sind lokal gekapselt. Alte klassische Lovelace-Ressourcen und automatisch geladene HA-Module können dieselbe Version ohne Namenskonflikte laden.
- Browserprüfungen decken mehrere Ressourcenadressen, klassische Skripte, Module, beide nativen HA-Panels und die Migration von v2 bis 2.3.1 ab. Bestehende Bereiche, Szenen und Lampensteuerung bleiben unverändert; keine erneuten Hardware-Schalttests.
- Automatische Push-Prüfungen laufen auf `main`; vollständige Pull Requests werden weiterhin geprüft. Dateiweise vorbereitete Release-Zweige erzeugen so keine irreführenden roten Zwischenläufe mehr. Manuelle Prüfungen bleiben verfügbar.

## 2.3.1-beta.1

- Normale neue Lampen und ausdrücklich als Lampen ausgewählte Schaltaktoren verwenden die aktive Hauptspur statt der früher ausgeschalteten Gruppe „Andere“. Gespeicherte Szenen werden nicht automatisch umgeschrieben.
- Dashboard zeigt die tatsächlich wirksame Szenenzuordnung (aktive/ausgeschaltete Lampen); eine reine Aus-Szene wird deutlich gekennzeichnet. Lampenzeilen zeigen den zugeordneten Effekt der gewählten Szene.
- Separate Quelle „Schaltaktor als Lampe“: `switch.*` erhält ausschließlich `switch.turn_on` / `switch.turn_off`, einschließlich Rücksetzen. Explizites Blinken schaltet Relais höchstens alle acht Sekunden um. Farben und Helligkeit werden nicht an Relais gesendet.
- Kleine globale Option für den Seitenleisteneintrag unter Verbindung & Darstellung und im normalen HA-Optionsdialog. Die Dashboard-Karte und direkte Bedienroute bleiben auch bei ausgeblendeter Seitenleiste verfügbar.
- Lokale RGBW-Hardwareprüfung: Kerzenflackern, Farbwechsel, 55 % / 35 % Helligkeit und exakte Wiederherstellung vom Shelly über HA bestätigt. Die Ursache des gemeldeten Ausschaltens war die ausgeschaltete Gruppenspur; die HA-Farbkonvertierung arbeitete korrekt.
- Weitere Prüfdetails einschließlich Grenzen der alten HACS-Logoanzeige: `docs/TEST-2.3.1.md`.

## 2.3.0-beta.1

Öffentliche Vorabversion mit Studio A und Softwareeffekten für normale Home-Assistant-Lampen.

- Studio A umgesetzt: Bereichsleiste, kompakter Show-Player, Szenen und Atmosphäre nebeneinander, Lampenzeilen mit aufklappbaren Details. Einrichtung und Bedienung bleiben getrennt, alle bestehenden Funktionen erreichbar.
- Gewöhnliche HA-Lampen verwenden ausschließlich `light.turn_on` / `light.turn_off`. RGB wird von HA in unterstützte RGBW-/RGBWW-/HS-/XY-Modi übersetzt; Weißtemperaturen werden auf den Gerätebereich begrenzt, reine Ein/Aus-Lampen erhalten keine Farb- oder Dimmbefehle.
- Nicht vorhandene Geräteeffekte werden jetzt über langsame HA-Show-Frames umgesetzt statt durch statisches warmes Licht ersetzt. Maximal ein Frame pro Lampe alle zwei Sekunden; Geschwindigkeit beeinflusst den Verlauf. Ein/Aus-Lampen bleiben bei Farbeffekten an und wechseln nur bei ausdrücklich gewähltem Blinken zwischen An und Aus.
- Neue Standardpakete spielen auch in der Gruppe „Andere“. Gespeicherte Aus-Einstellungen bleiben erhalten. Eine sichtbare, ausdrücklich auszulösende Übernahme der Oben-Einstellung hilft bei älteren Paketen.
- Effekte werden vor dem Rücksetzen entfernt; getrennte Bereiche laufen unabhängig. Vorschau, Szenenwechsel und Rücksetzen werden mit der Frame-Steuerung abgestimmt.
- Automatisierte Tests und lokale Browserprüfung; noch kein Nachweis an den echten Shelly-/WLAN-Lampen. Details in `docs/TEST-2.3.md`.

## 2.2.0-beta.2

Öffentliche 2.2-Vorabversion mit gemischten Lampenquellen und sechs neuen Bedienfunktionen.

- Home-Assistant-Lampen unabhängig von Zigbee2MQTT auswählen; RGB, RGBW, RGBWW, Dimmer, Weißtemperatur und Ein/Aus je nach Gerätefähigkeit. Explizite HA-Anbindung wird nie auf direkte MQTT-Steuerung umgestellt.
- Favoriten pro Bereich, mehrere Bereiche gemeinsam starten/stoppen, Ausschalt-Timer und Shuffle-Runden ohne Wiederholungen.
- Bereiche mit Szenen/Paketen kopieren, Lampen neu zuordnen; kopierte Zeitpläne bleiben deaktiviert. Sanfte Übergänge für unterstützte statische HA-Lichtbefehle.
- Veraltete manuelle Dashboard-Ressourcen blockieren die neue Oberfläche nicht mehr. Browserprüfung mit tatsächlichen älteren v2-/v2.1-Karten bestanden; vorhandene Karten müssen nicht umgeschrieben werden.
- 81 Python-Tests, UI-Smoke-Test und interaktive Browserregression bestanden. Release zusätzlich durch HACS-/hassfest-Prüfungen und Browserregression auf GitHub abgesichert.
- Voraussetzung HA 2026.10+. Backup erstellen, Update über HACS installieren, HA neu starten und Browser neu laden. Timer werden bei Neustart/Reload gelöscht; native Geräteeffekte unterstützen nicht alle Übergänge. Vollständige neue Hardwaretests stehen weiterhin aus.


## 2.2.0-beta.1

Nur lokaler Teststand, nicht veröffentlicht.

- Lampenquellen Home Assistant / Zigbee2MQTT getrennt auswählen; HA-Lampen werden nicht automatisch auf direktes MQTT umgestellt.
- RGBW-/RGBWW-Zustände vollständig zurücksetzen; passende Befehle für reine Dimmer, Ein/Aus und Weißtemperaturen.
- Bereichsfavoriten, gemeinsame Bereichssteuerung, Ausschalt-Timer, Shuffle-Runden ohne Wiederholung, Bereichskopie und sanfte HA-Übergänge.
- 81 Python-Tests, UI-Smoke-Test und interaktive Demo-Browserprüfung. Noch kein neuer realer HA-/Hardwaretest.
- Details, Bedienung und Grenzen: docs/TEST-2.2.md.

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
