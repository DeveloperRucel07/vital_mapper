# Definition of Done – Vital Mapper Backend

Gilt fuer jede Person und jedes KI-Modell, das an diesem Projekt arbeitet
(siehe [`AGENTS.md`](AGENTS.md)). Referenzierte Anforderungs-IDs (F-xx,
NF-xx, UC-xx, R-xx) beziehen sich auf [`docs/anforderungen.md`](docs/anforderungen.md).

Drei Ebenen: **Code/PR** (jede Aenderung), **Feature/Use-Case** (ein
funktionsfaehiges Stueck Fachlichkeit), **MVP/Release** (das Gesamtsystem vor
echtem Einsatz). Eine Ebene gilt erst als erfuellt, wenn alle Punkte darin
abgehakt sind – nicht "im Wesentlichen" oder "bis auf Kleinigkeiten".

---

## Ebene 1: Code/PR (bei jeder Aenderung)

**Architektur**
- [ ] Clean-Architecture-Schichtung eingehalten (siehe AGENTS.md Abschnitt 1) –
      keine Domain→Infrastruktur-Abhaengigkeit, keine konkrete Adapterklasse
      ausserhalb von `interfaces/api/`
- [ ] Neue fachliche Logik liegt in `domain/` oder `application/use_cases/`,
      nicht in einem Router oder Adapter

**Qualitaet**
- [ ] `ruff check src tests` fehlerfrei
- [ ] `ruff format --check src tests` fehlerfrei
- [ ] `mypy src` (strict) fehlerfrei
- [ ] `bandit -r src -ll` ohne High/Critical Findings
- [ ] `pip-audit` ohne bekannte kritische Schwachstellen bei neuen/geaenderten
      Abhaengigkeiten
- [ ] `pytest` vollstaendig gruen
- [ ] Unit-Test(s) fuer jeden neuen oder geaenderten Use Case vorhanden

**Security**
- [ ] Keine Secrets, Tokens oder Passwoerter im Diff (`detect-secrets` gruen)
- [ ] Jede neue Route mit Patientenbezug nutzt `require_role` (und ggf.
      `check_patient_access`)
- [ ] Kein neuer direkter, ungeprüfter externer HTTP-Aufruf ausserhalb der
      bestehenden Adapter (Ollama/Whisper/FHIR)

**Privacy**
- [ ] Kein neues Feld mit Personenbezug ohne Datenminimierungs-Check
- [ ] Keine Duplizierung von Patientenstammdaten (nur `patient_ref`)
- [ ] Verschluesselung/Loeschkonzept beruecksichtigt, falls neue
      Audiodaten/Transkripte gespeichert werden (F-26/F-27)

**Nachvollziehbarkeit**
- [ ] Audit-Log- bzw. Provenance-Eintrag fuer jede neue schreibende Operation
      auf klinischen Daten (F-21/F-22/F-33)
- [ ] Docstring/Kommentar referenziert die betroffene Anforderungs-ID
- [ ] Falls die Extraktionslogik veraendert wurde: Grounding-Test
      (`tests/unit/test_grounding_check.py`) besteht weiterhin bzw. wurde
      erweitert (F-08)

---

## Ebene 2: Feature/Use-Case (ein vollstaendiger UC oder eine User Story)

- [ ] Erfuellt die Akzeptanzkriterien aus der zugehoerigen User Story bzw.
      dem Use Case (`docs/anforderungen.md` Kapitel 3/5)
- [ ] Fehlerfaelle behandelt und getestet: Netzwerk-/Verbindungsabbruch
      (F-34), fehlgeschlagene oder unsichere Transkription (F-32),
      FHIR-Uebertragungsfehler (F-23)
- [ ] FHIR-Ressourcen wurden gegen eine echte HAPI-FHIR-Testinstanz
      validiert (nicht nur die Ressourcen-Konstruktion lokal geprueft)
- [ ] RBAC end-to-end getestet: mindestens ein Fall mit berechtigter und
      einer mit unberechtigter Rolle
- [ ] Unsichere oder fehlende Extraktionen sind im Response-Payload sichtbar
      markiert (F-15), keine stillschweigend aufgefuellten Werte
- [ ] Bei Event-basierten Features: Konsument ist idempotent (mehrfache
      Zustellung desselben Events aendert das Ergebnis nicht)
- [ ] Manuelle Freigabe (`[Freigeben]`) bleibt synchron/transaktional, alle
      Folgeeffekte laufen ueber den Event-Bus (Konsistenzprinzip, Kapitel 11.4)

---

## Ebene 3: MVP/Release (vor produktivem Einsatz mit echten Patientendaten)

**Fachlich**
- [ ] Alle "Muss"-Anforderungen aus `docs/anforderungen.md` Kapitel 4
      umgesetzt und manuell abgenommen
- [ ] Vertikaler Schnitt (mind. UC-02, siehe Kapitel 13) laeuft Ende-zu-Ende
      gegen eine echte HAPI-FHIR-Instanz

**Regulatorisch/Datenschutz**
- [ ] DSFA (R-02) abgeschlossen, bevor echte Patientendaten verarbeitet
      werden
- [ ] MDR-Klassifizierung (R-01) liegt vor
- [ ] Loeschkonzept (F-27) technisch verifiziert: Retention-Job laeuft
      nachweislich und loescht Audiodaten nach Ablauf der Frist
- [ ] `StubDeidentifier` durch eine produktionsreife Implementierung ersetzt
      oder der verbleibende Platzhalter ist als bewusst akzeptiertes Risiko
      dokumentiert (F-37–F-39)

**Sicherheit**
- [ ] Security-Review bzw. Penetrationstest durchgefuehrt
- [ ] Audit-Trail Ende-zu-Ende nachvollziehbar: Provenance-Kette
      stichprobenartig geprueft (Wer, wann, welche Version, welche Aenderung)
- [ ] Keine offenen High/Critical-Findings aus `bandit` oder `pip-audit`

**Betrieb**
- [ ] Betriebsdokumentation/Runbook vorhanden (Start/Stop, Backup,
      Modell-Update fuer Ollama/Whisper, Wiederherstellung nach Ausfall)
- [ ] NFR-Zielwerte aus Kapitel 5 (Latenz, Verfuegbarkeit) gemessen, nicht
      nur angenommen
- [ ] Kein `TODO`/Platzhalter-Code im produktiv genutzten Pfad ohne
      dokumentierte, bewusste Risikoabnahme
