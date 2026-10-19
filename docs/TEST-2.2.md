# 2.2-Beta: Bedienung und Prüfstatus

Öffentliche Version: 2.2.0-beta.2. Entwicklungszweig: `dev/mixed-light-sources`. Die native HA-Einrichtung wurde am vorhandenen 2.1-System geprüft; dort wurde außerdem eine Versionskollision mit einer alten manuellen Dashboard-Ressource nachgewiesen. Die Korrektur ist mit tatsächlichen älteren v2-/v2.1-Karten im Browser getestet. Vollständige neue Hardwaretests bleiben erforderlich.

## Ausprobieren ohne echte Lampen

`dev-preview.html` lokal im Browser öffnen. Die Vorschau startet mit Beispieldaten; über **Integration einrichten → Bereich wählen → Lampen** die neue Auswahl ausprobieren. Änderungen bleiben nur in der geöffneten Sitzung. Neuladen setzt die Demo zurück. Es gibt keine Verbindung zu Home Assistant, MQTT oder echten Lampen.

- **Home Assistant:** alle verfügbaren `light.*`-Entitäten, auch Shelly, WLAN, RGB, RGBW und RGBWW. Neue Lampen verwenden diesen Weg als Vorgabe. Es werden ausschließlich HA-Lichtaktionen gesendet. Automatische MQTT-Zuordnung kann diese Wahl nicht überschreiben.
- **Zigbee2MQTT:** die Auswahl beim Hinzufügen enthält nur erkannte, einer HA-Lichtentität zugeordnete Zigbee2MQTT-Lampen. Für native Dymera-Effekte und Tempo weiterhin direktes MQTT. Andere Z2M-Lampen werden über ihre HA-Entität gesteuert. Bei fehlender Erkennung kann jede vorhandene HA-Lampe über die erste Auswahl verwendet werden; eigenständige MQTT-Geräte ohne HA-Lichtentität werden nicht neu unterstützt.
- Jede Lampe zeigt ihre gemeldeten Fähigkeiten und die gewählte Anbindung. Beide Anbindungen dürfen im gleichen Bereich vorkommen. Bestehende Lampen ohne neues `transport`-Feld behalten die bisherige automatische Auswahl.
- RGB-Farben werden über die normale HA-Lichtaktion übertragen; Home Assistant passt sie an RGBW/RGBWW/HS/XY-Geräte an. Weißkanäle werden nicht im Szenen-Editor einzeln gemischt. Beim Rücksetzen bleiben vorhandene RGBW-/RGBWW-Kanalwerte und der aktive Farbmodus erhalten.
- Reine Dimmer erhalten Helligkeit; Ein/Aus-Leuchten erhalten keine Farb- oder Dimmparameter. Weißtemperaturen werden auf den Gerätebereich begrenzt. Nicht verfügbare Leuchten werden übersprungen. Geräteeffekte bleiben von den Fähigkeiten der Lampe abhängig.

## Sechs neue Alltagsfunktionen

1. **Favoriten:** im Dashboard Szene wählen und „Gewählte Szene merken“ drücken. Gespeicherte Favoriten starten unmittelbar über ihren eigenen Knopf. Favoriten gelten pro Bereich und sind Teil der Sicherung. Das Entfernen einer Szene oder eines Pakets bereinigt auch die Favoriten.
2. **Gemeinsame Bedienung:** Bereiche im Dashboard markieren und starten/stoppen. Gestartet wird dieselbe Paket-/Szenen-ID mit den jeweiligen Einstellungen des Zielbereichs. Vor einem gemeinsamen Start werden alle Ziele und aktive Lampenzuordnungen geprüft. Fehlt eine Szene, startet keiner der gewählten Bereiche. Befehle laufen anschließend nacheinander, ohne garantierte zeitliche Synchronisation. Laufzeitfehler/Hinweise werden je Bereich gemeldet; ein Hardwarefehler kann zu einer teilweisen Ausführung führen.
3. **Ausschalt-Timer:** zuerst Show starten, dann 15/30/60/120 Minuten oder 1–720 Minuten wählen. Timer beenden nur diesen Bereich und stellen dessen vorherige Lichtzustände bestmöglich wieder her. Szenenwechsel behalten den Timer. Entfernen oder manuelles Stoppen löscht ihn. Nach Ablauf gilt dieselbe Tages-Neustartsperre wie bei manuellem Stopp. Timer werden im Arbeitsspeicher gehalten und gehen bei HA-Neustart/Integrations-Reload verloren. Der Prüftakt beträgt fünf Sekunden.
4. **Shuffle-Runden:** standardmäßig alle ausgewählten Szenen einmal abspielen, dann neu mischen. Auch an der Rundengrenze wird die unmittelbar letzte Szene nicht sofort erneut gewählt. Abschaltbar über den neuen Schalter; feste Abläufe behalten ihre Reihenfolge. Runden werden bei manueller Szenenwahl und Neustart neu begonnen; keine dauerhafte Wiedergabehistorie.
5. **Bereich kopieren:** in der Integration den Quellbereich wählen und kopieren. Szenen, Pakete, Abläufe, Favoriten und Einstellungen werden unabhängig übernommen. Lampenliste und Einzelzuweisungen werden geleert, kopierte Wochen-/Jahreszeitpläne deaktiviert. Anschließend Lampen neu zuordnen und gewünschte Zeitpläne aktivieren.
6. **Sanfte Übergänge:** pro Bereich 0–30 Sekunden im Dashboard einstellen und speichern. Für statische HA-Farb-/Helligkeitsbefehle sowie Ausschalt-Szenen wird `transition` nur an Geräte gesendet, die die HA-Übergangsfunktion melden. Native Geräteeffekte und direkte Dymera-MQTT-Befehle wechseln ohne dieses Überblenden. Stoppen/Rücksetzen bleibt unmittelbar.

## Prüfung und Grenzen

81 Python-Tests bestanden, einschließlich Produktionsklassen mit simulierten HA-Zuständen und Lichtaktionen: Transportwahl, RGB/RGBW/RGBWW, Wiederherstellung, Timer, Bereichskopie, Gruppenvorprüfung, Teilfehler und mehrere vollständige Shuffle-Runden. UI-Smoke-Test sowie interaktive Browserprüfung mit Beispieldaten bestanden. Letztere prüft neue Lampenquellen, Filter, Speichern, Favoritenstart, Timer setzen/entfernen, gemeinsame Bedienung, Rundenschalter, Übergangsoption, Kopie, Mobilansicht und Themefarben. Die Demo ersetzt keine HA-Laufzeitprüfung.

Vor Veröffentlichung auf einer separaten HA-Testinstallation zusätzlich echte RGBW-/RGBWW-Leuchten, gemischte Bereiche, Timerablauf, MQTT-Wiederverbindung und Geräteübergänge prüfen. Der Release-Workflow führt vor Tag und Veröffentlichung offizielle HACS-/hassfest-Prüfungen und die Browserregression einschließlich alter Karten aus. Das lokale Installationspaket dient dem Test auf einer gesicherten Testinstallation; vorher vollständiges HA-Backup und Export der Studio-Einstellungen anlegen.

Grundlage: [HA-Lichtaktionen](https://www.home-assistant.io/actions/light.turn_on/) und [offizielle Lichtfähigkeiten](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/light/const.py).
