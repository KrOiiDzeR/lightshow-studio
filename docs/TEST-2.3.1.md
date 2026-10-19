# Lampenzuordnung, Schaltaktoren und Seitenleiste

## Bestätigte Ursache und Korrektur

In einer realen Einrichtung war eine normale RGBW-Leuchte der Gruppe **Andere** zugeordnet. Alle 15 gespeicherten Szenen enthielten für diese Gruppe **Aus**. Der Runner führte diesen gespeicherten Ausschaltbefehl korrekt aus; beim Stoppen stellte er den ursprünglichen Zustand wieder her.

Neue normale Leuchten verwenden deshalb jetzt **Hauptlicht / Oben**. Bestehende Einrichtungen werden nicht still verändert. Bei betroffenen Lampen unter **Konfiguration → Lampen → Bearbeiten → Gruppe** die passende aktive Spur wählen oder im Editor bewusst einen Effekt für Andere festlegen. Einzel-Ausnahmen haben weiterhin Vorrang. Das Dashboard zählt vor dem Start, wie viele Lampen die gewählte Szene einschaltet beziehungsweise ausschaltet, und kennzeichnet reine Aus-Szenen. Die Lampenliste zeigt den tatsächlich zugeordneten Effekt der gewählten Szene.

## Fähigkeiten und Schaltaktoren

HA meldet die verfügbaren Farbmodi; diese werden für Farbe, Weißtemperatur und Helligkeit berücksichtigt. RGB wird über die reguläre HA-Lichtaktion übergeben. Die HA-Light-Integration übersetzt es für RGBW/RGBWW/HS/XY-Geräte in ein unterstütztes Format. Helligkeits- und Weißkanäle werden beim Stoppen im ursprünglichen aktiven Farbmodus wiederhergestellt.

Eine als `switch.*` angelegte Leuchte wird über **Lampenquelle → Schaltaktor als Lampe (Ein/Aus)** ausdrücklich ausgewählt. Nur Aktoren wählen, die tatsächlich Lampen versorgen. Relais werden niemals automatisch durch die Lampensuche aufgenommen. Sie erhalten ausschließlich Schaltbefehle, keine Farb-/Dimm-/MQTT-Befehle. Farbeffekte bedeuten dort An; Aus und Helligkeit 0 bedeuten Aus. Nur ausdrücklich gewähltes Blinken wechselt den Zustand, mit mindestens acht Sekunden zwischen Relaisumschaltungen.

## Reale Prüfergebnisse

Am Shelly RGBW2 bestätigt HA `supported_color_modes: rgbw`; dies ist kein RGBWW-Gerät. Nach Korrektur der Gruppenzuordnung wurden über die vorhandene Integration geprüft:

- Kerzenflackern: Lampe bleibt an; Helligkeit und Farbkanäle ändern sich über mehrere Messpunkte.
- Farbwechsel: HA meldet farbige RGBW-Werte.
- Statisches Warmweiß bei 55 % und 35 %: HA meldet Helligkeiten 140 beziehungsweise 89 von 255.
- Stoppen nach den Tests: ursprüngliche Helligkeit und sämtliche vier RGBW-Kanäle werden exakt wiederhergestellt.

Zusätzlich mit der echten Wohnzimmerleuchte als `switch.*` getestet: Eine aktive Szene schaltet sie ein, eine ausdrücklich konfigurierte Aus-Szene schaltet sie aus. Stoppen stellt sowohl einen zuvor ausgeschalteten als auch einen zuvor eingeschalteten Zustand wieder her. Die Geräteantwort wurde jeweils nach ihrer Aktualisierung ausgewertet. Der dafür angelegte Testbereich wurde anschließend entfernt; vorhandene Bereiche und Szenen bleiben erhalten.

Das sind Rückmeldungen des echten Geräts über Home Assistant. Eine Sichtprüfung der physischen LED-Stufen durch eine Kamera oder eine anwesende Person ist damit nicht ersetzt. RGBWW-, HS-, XY-, reine Dimmer- und Light-Ein/Aus-Modi werden zusätzlich automatisiert geprüft. Eine physische RGBWW-Leuchte wurde nicht als solche identifiziert.

## Seitenleiste

Unter **Konfiguration → Verbindung → Lightshow Studio in der Seitenleiste anzeigen** oder im normalen HA-Optionsdialog aktivieren/deaktivieren und übernehmen. Diese globale Änderung gilt für alle Benutzer und lädt die Integration neu; Shows vorher stoppen. Die direkte Bedienroute `/lightshow-studio`, die Konfiguration über Geräte & Dienste und die vorhandene Dashboard-Karte bleiben erreichbar.

Live geprüft: ausblenden → Seitenleisteneintrag verschwindet, Konfigurationsroute bleibt erreichbar; wieder einblenden → Eintrag erscheint wieder. Ein dabei gefundener Fehler mit einer unzulässigen Bereichs-ID bei globalen Einstellungen wurde korrigiert und durch eine Browser-Regressionsprüfung abgesichert. Die Tests endeten mit aktivierter Seitenleiste und ohne laufende Testshow.

Automatisierte Prüfung: 96 Python-Tests, UI-Smoke-Test, vollständige Browserprüfung mit gemischten Quellen, Bereichen, Migration, Timer, Favoriten, Shuffle, Mobilansicht und Themes. Home Assistant `ha core check` war vor beiden Testneustarts erfolgreich.

## Logo in Home Assistant und HACS

Das gültige lokale Logo liegt in `custom_components/lightshow_studio/brand/icon.png`. Home Assistant ab 2026.3 lädt solche Bilder über seine Brands-Proxy-API. Das Logo wird in der HA-Integrationsansicht korrekt dargestellt.

HACS 2.0.5 mit Frontend 20250128065759 verwendet in seiner Repositoryliste noch die zentrale externe Brands-Quelle. Dieses ältere Frontend berücksichtigt lokal mitgelieferte Logos dort nicht. Zusätzliche neue Custom-Integration-Logos werden im zentralen Brands-Repository seit Einführung der Proxy-API nicht mehr angenommen. Ein weiteres `icon.png` im Repository-Hauptordner oder eine frei erfundene `hacs.json`-Option behebt diese Einschränkung nicht. Die HACS-Listenanzeige benötigt entsprechende Unterstützung im HACS-Frontend; HACS wird von dieser Integration nicht gepatcht.

Offizielle Grundlagen: [HA-Farbmodi](https://contributors.home-assistant.io/core/entities/light/), [Shelly-Lampen und Schaltaktoren](https://www.home-assistant.io/integrations/shelly/), [lokale Markenbilder](https://contributors.home-assistant.io/core/integrations/file-structure/), [Brands-Repository und Proxy-Umstellung](https://github.com/home-assistant/brands).
