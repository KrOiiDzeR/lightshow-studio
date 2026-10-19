# Studio A und normale Home-Assistant-Lampen

Vorabversion 2.3.0-beta.1, entwickelt und lokal geprüft auf `dev/studio-ha-lights`.

## Was korrigiert wurde

Die bisherige HA-Anbindung nutzte bereits normale Lichtaktionen. Zwei Einschränkungen verhinderten jedoch das erwartete Ergebnis: In älteren Standardpaketen war die automatisch zugeordnete Gruppe **Andere** in allen Szenen ausgeschaltet. Fehlende native Geräteeffekte wurden außerdem nur als statisches warmes Licht ausgegeben.

Neue Pakete verwenden für Andere dieselbe Ausgangsstimmung wie Oben, mit getrennten Kopien der Einstellungen. Bestehende Pakete und ausdrücklich gespeicherte Aus-Einstellungen werden nicht überschrieben. Unter **Konfiguration → Lampen** erscheint bei betroffenen Zuordnungen ein Hinweis mit einer Übernahme-Schaltfläche. Diese übernimmt für alle ausgeschalteten Andere-Gruppen dieses Bereichs die jeweilige Oben-Einstellung. Einzelne Lampenausnahmen bleiben erhalten. Vor dem Speichern im Editor prüfen; mit Verwerfen bleibt die bisherige Konfiguration bestehen.

## Steuerung über Home Assistant

Unter **Lampen → Anbindung: Home Assistant** wird niemals direkt an MQTT gesendet. WLAN, Shelly und andere Integrationen werden über ihre vorhandenen `light.*`-Entitäten bedient.

| Lampe | Verhalten |
| --- | --- |
| RGB / RGBW / RGBWW / HS / XY | RGB-Farbbefehle und Helligkeit über `light.turn_on`; HA übernimmt die unterstützte Farbkonvertierung |
| Weißtemperatur | Helligkeit und passende, begrenzte Kelvinwerte |
| Dimmer | Helligkeit; keine Farbbefehle |
| Nur Ein/Aus | An/Aus; Farbeffekte werden als An dargestellt, ausdrückliches Blinken als langsames An/Aus |
| Verfügbarer passender Geräteeffekt | Der von der Lampe angebotene Effekt |
| Kein passender Geräteeffekt | Softwareeffekt über normale HA-Lichtaktionen; maximal ein neuer Frame alle zwei Sekunden |

Softwareeffekte bilden Kerzenflackern, Kamin, Atmen, Funkeln und Farbverläufe nach. Sie sind wegen der begrenzten Befehlsrate bewusst langsamer als lokale Lampeneffekte. Sonnenauf- und -untergang bleiben nach ihrem Verlauf beim Endzustand. Hardware ohne Farbe kann keine Farbe darstellen; ein Relais kann nicht dimmen. Vorhandene `switch.*`-Entitäten werden nicht automatisch als Lampen behandelt; diese gegebenenfalls mit Home Assistants „Switch as X“ als Licht verfügbar machen.

Beim Stopp wird der zuvor gespeicherte Zustand wiederhergestellt, einschließlich aktiver RGBW-/RGBWW-Weißkanäle. Effekte, Timer und Snapshots sind Laufzeitdaten, die bei einem HA-Neustart nicht erhalten bleiben. Softwareeffekte werden beim Entladen beendet. Gerätespezifische native Dymera-Effekte bleiben über Zigbee2MQTT erhalten.

## Studio A

Bereiche links auswählen, oben den gewählten Bereich und seinen Status sehen. Shows starten/stoppen direkt im Player, Atmosphäre neben den Szenen. Favoriten, Abläufe, Timer, gemeinsame Bedienung und Übergänge bleiben erreichbar. Zusätzliche Bedienfunktionen sind aufklappbar. Die Konfiguration zeigt kompakte Lampenzeilen mit Quelle, Fähigkeiten und Gruppe; **Bearbeiten** klappt die Details auf. Bei schmalen Anzeigen wechseln die Bereiche in eine horizontale Leiste. HA-Themes und transparente Grundflächen bleiben unterstützt.

## Prüfumfang

Automatisierte Prüfungen führen die tatsächlichen Runner mit simulierten HA-Zuständen und Lichtaktionen aus: alle unterstützten Farbmodi, sämtliche Softwareeffekte, Begrenzung der Befehlsrate, Fehler bei der ersten Aktion, Stoppen, RGBWW-Rücksetzen und parallele Bereiche. Vorhandene Speicher-/MQTT-/Zeitplanprüfungen bleiben erhalten. Browserprüfung bedient echte Formulare, Bereiche, Shuffle, Favoriten, Timer, Import/Export und unterschiedliche Bildschirmgrößen; nur die Verbindung zu HA ist in der Vorschau simuliert.

**Noch offen:** Installation und Sichtprüfung an den tatsächlichen Shelly-/WLAN-/Ein/Aus-Lampen. Die lokale Vorschau schaltet keine echten Lampen. Dafür diesen Teststand gezielt installieren, HA neu starten und jeweils nur einen Bereich testen. Bestehende Einrichtung vorher über die Integration exportieren. Die Vorabversion in HACS auswählen und installieren, HA neu starten und den Browser neu laden. Keine neuen YAML-Einträge erforderlich.

Ergebnis der lokalen Prüfung: **90 Python-Tests bestanden**, zusätzlich UI-Smoke-Test, Browserregression mit alten v2-/v2.1-/v2.2-Karten, Vorschau bei 320 und 390 Pixeln sowie Struktur-/Datenschutzprüfung und ZIP-Erstellung. Die asynchronen Vorschautests liefen mit einer echten Ereignisschleife außerhalb der eingeschränkten Testumgebung; diese benötigt unter Windows eine lokale Socket-Verbindung.

## Offizielle Grundlagen

- [HA-Light-Aktionen und Zustände](https://www.home-assistant.io/integrations/light/)
- [Farbmodi, automatische Konvertierung und unterstützte Eigenschaften](https://contributors.home-assistant.io/core/entities/light/)

Die Dokumentation bestätigt, dass HA eine angeforderte Farbe vor dem Geräteaufruf in einen unterstützten Farbmodus übersetzt. Ein zusätzlicher RGBW-/RGBWW-Treiber in Lightshow Studio ist deshalb nicht erforderlich. Die Standardaktion wird statt eines MQTT-Effektbefehls verwendet.
