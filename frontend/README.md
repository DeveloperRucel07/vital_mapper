# Vital Mapper Frontend

## 1. Analysebericht

### Kurzbericht vor der Implementierung

1. **Aktuelle Architektur:** FastAPI-Modularmonolith mit Clean Architecture,
   PostgreSQL und lokalen Ollama-/Whisper-/FHIR-Adaptern.
2. **Vorhandene Backend-Funktionen:** Login, Admin-Benutzeranlage,
   patientenbezogene Draft-Zugriffsprüfung, Korrekturen und transaktionale
   Freigabe vorhandener Drafts.
3. **Authentifizierung:** Kurzlebiges JWT als Bearer-Response; keine
   serverseitige Session und kein Token-Widerruf.
4. **API-Endpunkte:** `GET /health`, `POST /auth/login`, `POST /auth/users`,
   `POST /drafts/{draft_id}/approve` und
   `POST /drafts/{draft_id}/corrections`.
5. **Datenmodelle:** User, Recording, Transcript, Extraction, CareReportDraft,
   Correction, Approval, OutboxEvent und AccessGrant; Patientenstammdaten
   werden nur über `patient_ref` referenziert.
6. **Security:** Scrypt-Passwort-Hashing, JWT-Claims, Rollenprüfung,
   Vertretungs-Grant-Prüfung und strukturiertes Zugriffslogging.
7. **Schwachstellen/Lücken:** fehlendes `/auth/me` und `/auth/logout`, keine
   CORS-Konfiguration, kein manipulationssicherer Audit-Speicher und ein noch
   nicht angebundener regulärer Pflegezuweisungs-Check.
8. **Fehlende Frontend-APIs:** Patientensuche, Recording-Upload,
   Transkription, Extraction, Berichtsentwurf, Draft-Lesen/-Ändern und
   FHIR-Vorschau/-Status.
9. **Frontend-Architektur:** React/Vite mit strikt typisierten API-Modellen,
   zentralem API-Client, Feature-Logik für Auth und Recorder sowie einer
   kleinen, geschützten Seitenstruktur.
10. **Implementierungsschritte:** sichere Login-Basis, Dashboard und
    Capability-Hinweise, Patientenkontext, flüchtiger Recorder,
    schrittweiser Review-Rahmen, Tests und vollständige Build-/Security-Checks.

### Aktuelle Architektur

Das Repository enthält ein Python/FastAPI-Backend mit Clean Architecture:
`domain`, `application`, `infrastructure` und `interfaces/api`. PostgreSQL
persistiert Benutzer, Aufnahmen, Transkripte, Extraktionen, Entwürfe,
Korrekturen, Freigaben und Outbox-Ereignisse. Ollama, Whisper und HAPI FHIR
sind als lokale Adapter vorgesehen.

### Vorhandene Backend-Funktionen

Implementiert sind Login, die administrative Benutzeranlage, die Prüfung von
Patientenzugriffen im Draft-Kontext, Korrektur-Erfassung und die transaktionale
Freigabe eines vorhandenen Drafts. Die Domäne enthält außerdem Modelle und
Use Cases für Transkription, Extraction, FHIR und Events; die dafür nötigen
HTTP-Routen sind aktuell noch nicht exponiert.

### Authentifizierung und Autorisierung

`POST /auth/login` gibt ein kurzlebiges JWT als Bearer-Token zurück. Das
Frontend hält dieses Token ausschließlich im flüchtigen JavaScript-Speicher;
es wird nicht in `localStorage`, `sessionStorage`, IndexedDB oder URLs abgelegt.
Das Backend validiert Rollen über `require_role` und patientenbezogenen Zugriff
über `check_patient_access`. Eine echte Server-Session, Token-Widerruf und
`/auth/me` sind aktuell nicht vorhanden.

### Verfügbare API-Endpunkte

| Endpoint | Verwendung im Frontend | Status |
| --- | --- | --- |
| `GET /health` | Infrastrukturdiagnose | vorhanden, nicht im UI genutzt |
| `POST /auth/login` | Anmeldung | verwendet |
| `POST /auth/users` | Benutzeranlage durch Admin | vorhanden, keine UI im MVP |
| `POST /drafts/{draft_id}/approve` | Freigabe eines vorhandenen Drafts | vorhanden, noch nicht erreichbar ohne Draft-Lese-/Erstell-API |
| `POST /drafts/{draft_id}/corrections` | Korrekturen eines vorhandenen Drafts | vorhanden, noch nicht erreichbar ohne Draft-Lese-/Erstell-API |

Nicht vorhanden sind insbesondere `/auth/me`, `/auth/logout`, Patienten-CRUD
oder -Suche, Recording-Upload, Transkription, Extraction, Berichtsentwurf,
Draft-Lesen/-Ändern und FHIR-Validierung/-Status.

### Relevante Security-Befunde

Die API nutzt Bearer-JWTs statt HttpOnly-Cookies. Dadurch ist das Frontend auf
flüchtige In-Memory-Sessions begrenzt, und ein Reload beendet die Sitzung.
Eine CORS-Konfiguration ist im Backend nicht vorhanden; die lokale Entwicklung
verwendet deshalb einen Vite-Proxy. Der Audit-Adapter schreibt derzeit ein
strukturiertes Log, aber noch keine manipulationssichere Append-only-Senke.
Die reguläre Pflegezuweisung ist in `check_patient_access` noch ein TODO; im
MVP wird ausschließlich ein aktiver Vertretungs-Grant geprüft.

## 2. Implementierte Frontend-Architektur

Das Frontend liegt vollständig unter `frontend/` und verwendet React,
TypeScript, Vite und Vitest ohne UI- oder State-Management-Großdependency.
Die Trennung ist:

```text
App / Seiten
  -> Feature-Logik (Auth, Recorder)
    -> zentraler ApiClient und typisierte API-Modelle
      -> FastAPI-Backend
```

Der Recorder ist als kleine Zustandsmaschine umgesetzt. Mikrofonzugriff wird
erst nach ausdrücklicher Aktion angefordert, Audio bleibt nur temporär als
Blob/URL im Speicher und wird beim Verlassen des Workflows freigegeben. Es
gibt keine ungeprüfte HTML-Ausgabe und keine Client-Logs mit Gesundheitsdaten.

## 3. Seiten und UX

- Login mit Loading-, Fehler- und Session-Zuständen.
- Dashboard mit Schnellstart, Statuskarten und transparenter Backend-Lücke.
- Patientensuche mit sichtbarer Patientensicherheitswarnung; ohne vorhandene
  API werden keine erfundenen Treffer angezeigt.
- Dokumentationsworkflow mit dauerhaft sichtbarem Patientenkontext,
  Entwurfsstatus, Recorder, Aufnahmezuständen und gesperrten Folge-Schritten.
- Responsive Navigation, Tastaturfokus, semantische Labels und nicht nur
  farbbasierte Statusanzeige.

## 4. Installation, Start und Build

```bash
cd frontend
npm install
npm run dev
npm run build
npm test
```

### Docker Compose

Der Produktions-Build ist als eigener, nicht-rootfähiger Container vorbereitet:

```bash
docker compose up --build
```

Das Frontend ist anschließend unter `http://localhost:3000` erreichbar. Der
Nginx-Container liefert die statischen Dateien aus und proxied `/backend/`
intern an den FastAPI-Service. Dadurch läuft der Browser-Request same-origin;
eine zusätzliche CORS-Freigabe für das Frontend ist im Compose-Betrieb nicht
nötig. Der Node-Build läuft nur in der Build-Stage und ist nicht Bestandteil
des Runtime-Images.

`VITE_API_BASE_URL` ist die einzige Frontend-Umgebungsvariable. Standardmäßig
ist sie `/backend`; der Vite-Entwicklungsserver proxied diesen Pfad auf
`http://localhost:8000`. Im produktiven Reverse Proxy muss `/backend` auf das
Backend zeigen oder `VITE_API_BASE_URL` auf die öffentliche API-Basis gesetzt
werden. Secrets, Datenbankpasswörter, FHIR-Tokens und JWT-Schlüssel gehören
nicht in das Frontend.

## 5. Security- und Privacy-Entscheidungen

- Bearer-Token nur im Speicher; Logout leert Token, User und Patientenkontext.
- Keine dauerhafte Speicherung von Patienten-, Audio-, Transkript- oder
  Berichtsdaten im Browser.
- Keine `console.log`-Ausgaben mit sensiblen Daten.
- Einheitliche, nicht-technische API-Fehlerklassen für 401/403/404/409/422/5xx
  und Netzwerk-/Timeout-Fehler.
- Aufnahme startet nie automatisch und wird bei Navigation beendet.
- Klinische Schritte bleiben bis zur realen Backend-Unterstützung gesperrt;
  Mock-Daten werden nicht als echte Patientendaten ausgegeben.
- HTTP-Security-Header (CSP, HSTS, Referrer- und Permissions-Policy) müssen im
  Reverse Proxy bzw. in der Auslieferung gesetzt werden; das Vite-Bundle kann
  diese Header nicht verlässlich ersetzen.

## 6. Offene Backend-Capabilities

Für den vollständigen UC-01/UC-02-Workflow benötigt das Backend mindestens:

1. `GET /auth/me` und eine definierte Logout-/Widerrufsstrategie.
2. Geschützte Patientensuche mit minimalem `patient_ref`-Payload und
   `require_role` plus `check_patient_access`.
3. Recording-Upload inklusive verschlüsselter Speicherung und Retention.
4. Transkriptions-, Extraction- und Pflegebericht-Endpunkte mit typisierten
   Responses, `unsichere_felder` und Modellversionen.
5. Draft-Lese-/Änderungsroute, FHIR-Vorschau und Ergebnisstatus.
6. CORS oder einen dokumentierten, sicheren Reverse-Proxy sowie eine
   manipulationssichere Audit-Senke.

Diese Routen müssen zuerst fachlich und sicher implementiert werden; das
Frontend erfindet keine Requests oder Responses dafür.
