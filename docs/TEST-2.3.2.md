# Ladefehler bei mehreren Ressourcenadressen

## Ursache

Die Version 2.3.1 konnte bei genau einer Ressourcenregistrierung laden. Wurde dieselbe Version jedoch über zwei verschiedene URLs geladen, behandelte die Migrationshilfe die zweite Registrierung wie ein Versionsupdate. Sie ersetzte Methoden ihrer eigenen Basisklasse durch eine Weiterleitung auf eine davon abgeleitete Klasse. Das erzeugte eine Endlosschleife: `Maximum call stack size exceeded`; Karten und native Bedien-/Konfigurationsseiten konnten leer bleiben.

Ein isolierter Browserlauf hat diesen Fehler mit dem unveränderten 2.3.1-Code reproduziert. Die bestehende angemeldete HA-Sitzung konnte nach einem vollständigen Neuladen beide Seiten anzeigen; die konkrete Ressourcenhistorie anderer Browser wurde nicht ausgelesen. Der reproduzierte Fehler wird unabhängig von dieser Historie korrigiert.

## Korrektur

Jede Frontend-Version registriert ihre Klassen nur einmal. Wiederholte Aufrufe derselben Version verändern weder deren Prototypen noch bestehende Karten. JavaScript-Deklarationen sind außerdem gekapselt, damit klassische Lovelace-Skripte und HA-Module keine globalen Namenskonflikte erzeugen.

Die Version 2.3.2 hat eine neue Ressourcenadresse zur Cache-Aktualisierung. Es müssen keine YAML-Dateien oder Ressourcen von Hand bearbeitet werden. Vorhandene Bereiche, Lampenzuordnungen, Pakete und Szenen werden nicht verändert.

## Prüfungen

- Derselbe Code mehrmals als klassisches Skript im selben Kontext: Klassen und Render-Methode bleiben unverändert.
- Dieselbe Version über vier zusätzliche HTTP-Ressourcenadressen, gemischt als Modul und klassisches Skript: keine Browserfehler, vorhandene Karte und ihre Einstellungen bleiben erhalten.
- Native Bedien- und Konfigurationspanels: Eigenschaften sowohl vor als auch nach Einfügen in die Seite setzen; beide Ansichten laden.
- Gespeicherte v2-, v2.1-, v2.2- und v2.3.1-Ressourcen vor dem aktuellen Modul: Karten sowie native Panels zeigen die aktuelle Oberfläche.
- Bestehende vollständige Browserprüfung und 96 Python-Regressionstests erfolgreich. Es wurden dafür keine echten Lampen geschaltet.

Die roten GitHub-Läufe während der dateiweisen Vorbereitung von 2.3.1 gehören zu unvollständigen Zwischenständen auf dem Release-Zweig. Die abschließenden Pull-Request-, Main- und Release-Prüfungen von 2.3.1 waren erfolgreich. Die bisherige Browserprüfung erfasste alte Versionen vor einer neuen Version, aber nicht mehrere Ressourcenadressen derselben Version. Diese Lücke ist jetzt im bereits vorhandenen CI-/Release-Browserlauf geschlossen.

Push-Prüfungen werden künftig auf `main` ausgeführt. Pull Requests werden unverändert vollständig geprüft, und manuelle Prüfläufe bleiben verfügbar. Dadurch erscheinen beim dateiweisen Vorbereiten eines Release-Zweigs keine fehlgeschlagenen Läufe unvollständiger Zwischenstände mehr.

## Update

In HACS **Lightshow Studio → Informationen aktualisieren → Erneut herunterladen/Aktualisieren → v2.3.2-beta.1** wählen, Home Assistant neu starten und den Browser vollständig neu laden. Die Integration nicht entfernen oder neu einrichten; der vorhandene Konfigurationseintrag wird weiterverwendet.
