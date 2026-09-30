# Datenschutz und Informationssicherheit

## Zweck und Geltungsbereich

Dieses Dokument protokolliert Datenschutz- und Sicherheitsmassnahmen im
Vital-Mapper-Projekt. Es ergaenzt die fachlichen Anforderungen in
`docs/anforderungen.md`, ersetzt diese aber nicht. Massgeblich sind insbesondere
F-26 bis F-39, NF-06 sowie R-02 und R-05.

Jede technische Aenderung mit Datenschutz- oder Sicherheitsbezug wird hier mit
Datum, betroffenen Anforderungen, geaenderten Komponenten, Verifikation und
verbleibendem Restrisiko dokumentiert. Das Dokument ist kein Ersatz fuer eine
Datenschutz-Folgenabschaetzung (DSFA), ein Verzeichnis von
Verarbeitungstaetigkeiten oder eine regulatorische Freigabe.

## Schutzgegenstaende

- verschluesselte Rohaudiodaten und ihre Referenzen
- Transkripte und daraus abgeleitete klinische Informationen
- Pflegebericht-Entwuerfe, Korrekturen und Freigaben
- pseudonyme Patientenreferenzen (`patient_ref`)
- Benutzer-, Rollen-, Zugriffs- und Auditdaten
- OIDC-Sitzungen sowie Zugriffs- und Aktualisierungstoken
- Modellversionen, Outbox-Events und Interoperabilitaetsdaten

Patientenstammdaten wie Name, Geburtsdatum oder Adresse duerfen im Vital-Mapper-
Backend nicht dupliziert werden. Fuer persistierte klinische Daten wird nur die
externe `patient_ref` verwendet.

## Aktueller Stand

Stand: 2026-09-30

### Bereits vorhandene Kontrollen

| Bereich | Vorhandene Massnahme | Anforderung |
|---|---|---|
| Datenminimierung | Persistente klinische Datensaetze verwenden `patient_ref` statt lokaler Patientenstammdaten. | F-28 |
| Audioablage | Hochgeladene Audiodaten werden mit Fernet verschluesselt und ohne Originaldateinamen gespeichert. | F-26 |
| Dateizugriff | Audio-Referenzen werden gegen Path Traversal validiert. | F-26 |
| Audio-Retention | Ein Hintergrundprozess loescht abgelaufene Audiodateien nach `AUDIO_RETENTION_DAYS` und leert anschliessend ihre Referenz. | F-27 |
| Transkriptablage | Neue Transkripte werden mit einem versionierten Fernet-Format verschluesselt; vorhandene Klartexte werden vor Annahme von API-Verkehr beim Start migriert. | F-26 |
| Whisper-Verarbeitung | Der Whisper-Dienst verarbeitet Audio im Arbeitsspeicher und erzeugt keine temporaere Klartext-Audiodatei. | F-26 |
| Produktions-Transport | Produktionsstart wird bei HTTP-Service-URLs, unverschluesseltem Redis/Postgres, unsicherem BFF-Cookie, Legacy-Auth oder fehlendem separatem Transkript-Key abgewiesen. | F-26 |
| Container-Isolation | Backend, Frontend und Whisper laufen als unprivilegierte Benutzer; der Whisper-Port wird nicht mehr am Host veroeffentlicht. | F-26, R-05 |
| Authentifizierung | OIDC-BFF mit PKCE, Nonce, HttpOnly-Sitzungscookie und serverseitig verschluesselter Redis-Sitzung ist vorhanden. | F-30 |
| Autorisierung | Rollenpruefungen und patientenbezogene Zugriffspruefungen sind fuer die zentralen Dokumentationsrouten vorhanden. | F-30, F-31 |
| Grounding | Zahlen, Freitext, Boolean- und Enum-Fakten aus der KI-Extraktion werden gegen das Transkript geprueft. Unbelegte Werte werden vor der Anzeige geleert und als unsicher markiert. | F-08, F-15 |
| Menschliche Freigabe | Externe klinische Speicherung erfolgt erst nach expliziter Freigabe. | F-18, F-19 |
| Modellnachweis | Whisper- und Ollama-Versionen werden an mehreren Stellen gespeichert. | F-25 |
| Geheimnisse | Laufzeitgeheimnisse werden ueber `Settings` aus der Umgebung geladen; `.env` ist nicht versioniert. | F-26 |

### Offene Datenschutz- und Sicherheitsluecken

| Prioritaet | Befund | Betroffene Anforderungen |
|---|---|---|
| Hoch | TLS-Zertifikate, interne PKI und die tatsaechliche TLS-Terminierung werden ausserhalb dieses Repositories bereitgestellt und muessen im Zielbetrieb nachgewiesen werden. | F-26, R-05 |
| Kritisch | Bei Verbindungsabbruch existiert kein verschluesselter lokaler Aufnahme-Puffer und keine automatische Wiederaufnahme der Synchronisation. | F-34, UC-08 |
| Hoch | Auditdaten werden nur strukturiert geloggt; eine manipulationssichere, persistente Audit-Senke fehlt. | F-33, NF-06 |
| Hoch | Aenderungen an Transkript, Extraktion und Bericht erzeugen nicht durchgaengig automatisch einen Vorher-/Nachher-Nachweis. | F-21 |
| Hoch | Die Outbox besitzt keinen nachgewiesenen Worker fuer Retry, Idempotenz und Statusfortschritt. | F-20, F-23, F-33 |
| Hoch | Betroffenenrechte fuer Auskunft, Berichtigung und Loeschung sind nicht als vollstaendige Use Cases umgesetzt. | F-29 |
| Hoch | Die Deidentifikation ist nur ein Datums-Stub und nicht als produktionsreife Trainingsdaten-Pipeline umgesetzt. | F-37, F-38, F-39 |
| Mittel | Die Keycloak-Rollenzuordnung bildet nicht alle fuenf fachlichen Rollen ab. | F-30 |
| Mittel | Erteilung, Widerruf und Auditierung temporaerer Vertretungszugriffe sind nicht vollstaendig umgesetzt. | F-32 |
| Organisatorisch | Eine abgeschlossene DSFA, MDR-Klaerung und ein ISMS-Nachweis liegen im Repository nicht vor. | R-01, R-02, R-05 |

## Verifikation am 2026-09-29

Die Bestandsanalyse wurde ohne Aenderung klinischer Logik durchgefuehrt.

- Backend: 32 Tests erfolgreich
- Frontend: 6 Tests erfolgreich
- Frontend-Produktionsbuild erfolgreich
- `ruff check src tests`: erfolgreich
- `ruff format --check src tests`: erfolgreich
- `mypy src`: erfolgreich
- `bandit -r src -ll`: keine Befunde
- `pip-audit`: keine bekannten Schwachstellen in den aufloesbaren Abhaengigkeiten
- Gesamt-Testabdeckung des Python-Pakets: 55 Prozent

Die erfolgreichen Qualitaetspruefungen sind kein Nachweis der vollstaendigen
Anforderungserfuellung. Mehrere der oben genannten Datenschutzfaelle besitzen
noch keine automatisierten Tests.

## Datenschutz-Arbeitsprotokoll

### 2026-09-29 - Datenschutz-Bestandsaufnahme

**Art:** Analyse und Dokumentation, keine Aenderung produktiver Verarbeitung.

**Durchgefuehrt:**

- Anforderungen F-26 bis F-39, NF-06, R-02 und R-05 mit der Implementierung
  abgeglichen.
- Audioablage, Transkriptpersistenz, Whisper-Verarbeitung, RBAC,
  Patientenzugriff, Audit-Logging, Outbox, Deidentifikation und Browseraufnahme
  untersucht.
- Bestehende Backend- und Frontend-Tests sowie Security- und Quality-Gates
  ausgefuehrt.
- Offene Risiken priorisiert und in diesem Dokument festgehalten.

**Geaenderte Datei:**

- `docs/security.md` neu angelegt.

**Restrisiko:**

Alle unter "Offene Datenschutz- und Sicherheitsluecken" genannten Punkte bleiben
offen, bis eine technische oder organisatorische Massnahme implementiert,
getestet und in diesem Protokoll als abgeschlossen dokumentiert wurde.

### 2026-09-29 - Automatische Audio-Retention

**Anforderungen:** F-27

**Ziel:** Rohaudiodaten duerfen die konfigurierte maximale Aufbewahrungsdauer
nicht ueberschreiten.

**Umsetzung:**

- `EnforceAudioRetentionUseCase` berechnet einen UTC-Stichtag aus
  `AUDIO_RETENTION_DAYS` und verarbeitet faellige Aufnahmen in begrenzten
  Batches.
- Die verschluesselte Audiodatei wird zuerst idempotent geloescht. Erst danach
  wird die Datenbankreferenz geleert. Dadurch hinterlaesst ein DB-Fehler keine
  unreferenzierte Audiodatei; der naechste Lauf kann die Operation wiederholen.
- Ein kontrollierter Hintergrundprozess startet die Pruefung beim Backend-Start
  und wiederholt sie nach `AUDIO_RETENTION_CHECK_SECONDS`.
- Jede erfolgreiche Retention-Loeschung erzeugt ein strukturiertes Audit-Ereignis
  mit Systemakteur, Patientenreferenz und Zweck `delete_expired_audio`.
- Der Transaktionszugriff fuer Hintergrundaufgaben verwendet denselben
  konfigurierten SQLAlchemy-Session-Mechanismus wie die API.

**Geaenderte Komponenten:**

- `application/use_cases/enforce_audio_retention.py`
- `application/ports/repository_port.py`
- `infrastructure/persistence/repository.py`
- `interfaces/api/main.py`
- `interfaces/api/deps.py`
- `config.py`, `.env.example` und `docker-compose.yml`
- `tests/unit/test_audio_retention.py`

**Verifikation:**

- Abgelaufene synthetische Audiodatei wird geloescht und ihre Referenz geleert.
- Noch nicht abgelaufene Audiodatei bleibt erhalten.
- Zeitzonenloser Referenzzeitpunkt wird abgewiesen.
- Gezielte Tests: 4 erfolgreich.
- `ruff check src tests`: erfolgreich.
- `mypy src`: erfolgreich.

**Restrisiko und offene Punkte:**

- Das Audit-Ereignis wird weiterhin nur ueber die bestehende strukturierte
  Logging-Senke ausgegeben. Die manipulationssichere Audit-Persistenz aus NF-06
  bleibt offen.
- Mehrere Backend-Instanzen koennen denselben Retention-Lauf beginnen. Die
  Dateiloeschung ist idempotent; fuer groessere Installationen sollte zusaetzlich
  ein verteilter Scheduler-Lock eingefuehrt werden.

### 2026-09-30 - Verschluesselung von Transkripten und Whisper-Haertung

**Anforderungen:** F-26, R-05

**Ziel:** Audio und Transkripte duerfen weder unverschluesselt persistiert noch
in einer unsicheren Produktionskonfiguration transportiert werden.

**Umsetzung:**

- Neue Transkripte werden vor dem Schreiben in PostgreSQL mit Fernet
  verschluesselt. Das Speicherformat besitzt das Praefix `fernet:v1:`, damit
  spaetere Migrations- und Rotationsschritte die Version eindeutig erkennen.
- Lesen und Aktualisieren von Transkripten erfolgen ausschliesslich ueber die
  zentrale Ver- und Entschluesselungsfunktion.
- Beim Backend-Start werden vorhandene Klartexttranskripte idempotent und in
  begrenzten Batches verschluesselt. Die Migration ist abgeschlossen, bevor die
  Anwendung API-Verkehr annimmt.
- Entwicklung darf weiterhin lokale HTTP-Endpunkte verwenden. Fuer
  `APP_ENV=production` validiert `Settings` dagegen HTTPS fuer KI-, OIDC-, FHIR-
  und Gateway-Endpunkte, `rediss://` fuer Redis, SSL fuer PostgreSQL, sichere
  BFF-Cookies, deaktivierte Legacy-Authentifizierung und einen separaten
  `CLINICAL_DATA_ENCRYPTION_KEY`.
- Audio- und Transkript-Schluessel werden bereits beim Laden der Konfiguration
  auf das Fernet-Format geprueft. Produktionsbetrieb weist identische Audio- und
  Transkript-Schluessel ab. Validierungsfehler geben den fehlerhaften
  Schluesselwert nicht aus.
- Whisper liest Uploads mit einem Groessenlimit direkt in einen
  Arbeitsspeicherpuffer. Die vorherige temporaere Klartextdatei wurde entfernt.
- Der Whisper-Container besitzt einen eigenen unprivilegierten Benutzer und
  schreibt seinen Modellcache in dessen Home-Verzeichnis.
- Der Whisper-Port ist nur noch im Compose-Netz sichtbar und wird nicht am Host
  veroeffentlicht.
- Direkte Whisper-Abhaengigkeiten sowie die verwendete pip-Version wurden fest
  gepinnt und separat mit `pip-audit` geprueft.
- Nach einer Retention-Loeschung beantwortet der Transkriptionsworkflow den
  Zugriff kontrolliert mit HTTP 410 statt mit einem internen Dateifehler.

**Geaenderte Komponenten:**

- `config.py`
- `infrastructure/security/encryption.py`
- `infrastructure/persistence/repository.py`
- `interfaces/api/main.py`
- `application/use_cases/transcribe_recording.py`
- `domain/exceptions.py`
- `interfaces/api/routers/recordings.py`
- `whisper-service/main.py`, `whisper-service/Dockerfile` und
  `whisper-service/requirements.txt`
- `.env.example` und `docker-compose.yml`
- `tests/unit/test_transcript_encryption.py`
- `tests/unit/test_production_security_config.py`
- `tests/unit/test_recording_workflow.py`

**Verifikation:**

- Verschluesselungs-Roundtrip und Abwesenheit des Klartexts im Chiffrat getestet.
- Manipuliertes Transkript-Chiffrat wird abgewiesen.
- Startmigration kann Altdaten erkennen; Klartext bleibt nur fuer den
  kontrollierten Migrationspfad lesbar.
- Unsichere Produktionskonfiguration wird abgewiesen; vollstaendige sichere
  Beispielkonfiguration wird akzeptiert.
- Ungueltige Fernet-Schluessel und fehlende Schluesseltrennung werden vor dem
  Anwendungsstart erkannt; geheime Eingabewerte erscheinen nicht im Fehlertext.
- Zugriff auf durch Retention geloeschtes Audio wird fachlich abgewiesen.
- Python-Gesamtsuite: 42 Tests erfolgreich.
- Frontend: 6 Tests und Produktionsbuild erfolgreich.
- Ruff, Formatpruefung und Mypy erfolgreich.
- Bandit fuer `src` und `whisper-service`: keine Befunde.
- `pip-audit` fuer Backend und gepinnte Whisper-Anforderungen: keine bekannten
  Schwachstellen.
- `docker compose config --quiet`: erfolgreich.
- Whisper-Container-Build nach Pinning: erfolgreich.

**Build- und Supply-Chain-Ereignis:**

Der erste Whisper-Build mit unversionierten Abhaengigkeiten brach wegen eines
Paket-Hashkonflikts ab. Der Fehler wurde nicht ignoriert. Die direkten
Abhaengigkeiten wurden in `whisper-service/requirements.txt` gepinnt, pip wurde
auf eine feste Version gesetzt, die Anforderungen wurden auditiert und der
Container anschliessend erfolgreich neu gebaut.

**Restrisiko und offene Punkte:**

- Zertifikatsausstellung, interne PKI, Reverse Proxy und TLS-Terminierung liegen
  ausserhalb dieses Repositories. Der Code verhindert unsichere Produktions-URLs,
  ersetzt aber keinen Deployment-Nachweis.
- Fuer eine spaetere Schluesselrotation wird ein expliziter Key-Ring mit alter
  und neuer Schluesselversion benoetigt. Derzeit wird genau ein aktiver
  Transkript-Key erwartet.
- In der Entwicklungsumgebung darf bei fehlendem separatem Transkript-Key der
  Audio-Key als Fallback verwendet werden. Produktion verlangt Schluesseltrennung.
  Nach der Trennung bleiben vorhandene Entwicklungs-Chiffrate ueber einen
  kontrollierten Nur-Lese-Fallback entschluesselbar; neue Daten werden nur mit
  dem aktiven Transkript-Key geschrieben.
- Direkte Whisper-Abhaengigkeiten sind gepinnt; ein vollstaendiges Lockfile mit
  Hashes fuer alle transitiven Plattform-Wheels steht noch aus.
- Pflegebericht-Entwuerfe, Korrekturtexte und strukturierte Extraktionen koennen
  ebenfalls Gesundheitsdaten enthalten. Eine weitergehende Feldverschluesselung
  dieser Daten ist noch nicht umgesetzt und muss gegen Such-, Audit- und
  Interoperabilitaetsanforderungen abgewogen werden.

### 2026-09-30 - Vollstaendige technische Grounding-Pruefung

**Anforderungen:** F-08, F-09, F-15

**Ziel:** Eine KI-Extraktion darf keine klinischen Fakten enthalten, die nicht
im geprueften Transkript belegt sind.

**Umsetzung:**

- Die Extraktionssicherung prueft jetzt alle Felder des aktuellen
  `ClinicalExtraction`-Schemas: Zahlen, Freitext, Boolean-Aussagen und
  Enum-Werte.
- Pruefregeln erkennen explizite Schmerz- und Sturzverneinungen sowie klar
  formulierte Mobilitaets-, Orientierungs- und Reaktionsangaben.
- Unbelegte Modellwerte werden vor der Rueckgabe entfernt und mit ihrem
  Feldpfad in `unsichere_felder` markiert. Die Pflegefachkraft sieht damit
  keinen erfundenen Fakt als Vorschlag und kann die fehlende Angabe bewusst
  fachlich ergaenzen.
- `_assert_grounded` bleibt nach dieser Bereinigung aktiv und weist jeden noch
  unbelegten Wert als Sicherheitsnetz zurueck. Die Pruefung wurde nicht durch
  eine Prompt-Anweisung ersetzt oder optional gemacht.
- Tests decken unter anderem SpO2, Freitext, Boolean-Widersprueche,
  Mobilitaet, Orientierung, Sturz und Reaktion ab.

**Geaenderte Komponenten:**

- `src/vital_mapper/infrastructure/ollama/ollama_adapter.py`
- `tests/unit/test_grounding_check.py`

**Verifikation:**

- Grounding-Tests: 13 erfolgreich.
- Python-Gesamtsuite: 48 erfolgreich.
- `ruff check src tests`, `ruff format --check src tests` und `mypy src`:
  erfolgreich.
- `bandit -r src -ll`: keine Befunde.

**Restrisiko und offene Punkte:**

- Der Abgleich ist absichtlich konservativ. Sprachliche Umschreibungen, die
  nicht eindeutig einer hinterlegten Regel entsprechen, werden als unsicher
  behandelt statt als klinischer Fakt uebernommen.
- Die Regeln brauchen vor einem produktiven Rollout eine fachliche Evaluation
  mit reprasentativen, vollstaendig synthetischen Testtranskripten aus dem
  Pflegekontext. Die manuelle fachliche Pruefung bleibt verpflichtend.

## Vorlage fuer weitere Eintraege

### JJJJ-MM-TT - Kurztitel

**Anforderungen:** F-xx, NF-xx oder R-xx

**Ziel:** Beschreibung des Datenschutz- oder Sicherheitsziels.

**Umsetzung:**

- geaenderte Komponenten und fachliches Verhalten
- Datenminimierung, Aufbewahrung oder Zugriffsfolgen
- Migration beziehungsweise Auswirkung auf vorhandene Daten

**Verifikation:**

- ausgefuehrte Tests und Qualitaetspruefungen
- negative Sicherheits- beziehungsweise Missbrauchstests

**Restrisiko und offene Punkte:**

- verbleibende technische oder organisatorische Risiken
- notwendige externe Nachweise oder Entscheidungen
