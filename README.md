# Vital Mapper – Backend

Sprachgestuetzter Pflegedokumentationsassistent. Dieses Repository enthaelt
ausschliesslich das **Backend**; das Frontend folgt in einem separaten
Schritt.

- Fachliche Anforderungen, Architekturentscheidungen und Datenmodell:
  [`docs/anforderungen.md`](docs/anforderungen.md)
- Regeln fuer jedes KI-Coding-Tool, das hier arbeitet:
  [`AGENTS.md`](AGENTS.md)
- Verbindliche Abnahmekriterien: [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md)

## Architektur

Clean Architecture mit vier Schichten (`domain`, `application`,
`infrastructure`, `interfaces`) und Event-Driven-Kopplung zwischen den
Modulen ueber ein Postgres-Outbox-Pattern plus Redis. Details: Kapitel 10/11
in `docs/anforderungen.md`.

Tech-Stack: FastAPI, Ollama (Llama 3.x, lokal via Docker), ein eigenstaendiger
Whisper-Service (faster-whisper, eigener Container), PostgreSQL, Redis, HAPI
FHIR.

## Schnellstart

```bash
cp .env.example .env      # Werte anpassen, insbesondere Secrets/Keys
docker compose up --build
```

Danach einmalig das Ollama-Modell ziehen:

```bash
docker exec -it <ollama-container-name> ollama pull llama3.1:8b-instruct
```

API-Dokumentation danach unter `http://localhost:8000/docs`.

## Authentifizierung

Die API verwendet Username/Passwort zur Anmeldung und kurzlebige JWT-Bearer-
Tokens fuer geschuetzte Endpunkte. Passwoerter werden ausschliesslich als
scrypt-Hash gespeichert.

Anmeldung:

```http
POST /auth/login
Content-Type: application/json

{"username": "pflegekraft-test", "password": "<passwort>"}
```

Die Antwort enthaelt `access_token` und `token_type: "bearer"`. Benutzerkonten
werden ausschliesslich durch einen bereits authentifizierten Administrator
ueber `POST /auth/users` angelegt. Ein offener Bootstrap-Endpunkt fuer den
ersten Administrator ist absichtlich nicht vorhanden; die Erstinitialisierung
muss ueber eine kontrollierte Datenbank-/Deployment-Provisionierung erfolgen.
Fuer eine lokale Erstinitialisierung koennen temporaer `BOOTSTRAP_ADMIN_USERNAME`
und `BOOTSTRAP_ADMIN_PASSWORD` in `.env` gesetzt und danach wieder entfernt
werden:

```bash
python -m vital_mapper.interfaces.cli.create_admin
```

Wenn `DATABASE_URL` wie in der Docker-Konfiguration auf den Host `db` zeigt,
muss dieser Befehl innerhalb des Compose-Netzwerks ausgefuehrt werden:

```bash
docker compose exec backend python -m vital_mapper.interfaces.cli.create_admin
```

Ist der Backend-Container noch nicht gestartet, zuerst `docker compose up -d`
ausfuehren oder einmalig `docker compose run --rm backend python -m
vital_mapper.interfaces.cli.create_admin` verwenden.

## Entwicklung ohne Docker

```bash
pip install -e ".[dev]" --break-system-packages
uvicorn vital_mapper.interfaces.api.main:app --reload
```

## Qualitaetssicherung

```bash
pytest
ruff check src tests
ruff format --check src tests
mypy src
bandit -r src -ll
pip-audit
```

Alle fuenf Befehle muessen fehlerfrei laufen, bevor eine Aenderung als
abgeschlossen gilt (siehe `DEFINITION_OF_DONE.md`, Ebene 1).

## Frontend

Das React/TypeScript-Frontend liegt unter `frontend/`. Der Produktionsbetrieb
erfolgt über einen eigenen, nicht-rootfähigen Nginx-Container. Nach
`docker compose up --build` ist es unter `http://localhost:3000` erreichbar;
`/backend/` wird intern an FastAPI weitergeleitet.

Für reine Frontend-Entwicklung:

```bash
cd frontend
npm install
npm run dev
```

## Sicherheitshinweis

Dieses Projekt verarbeitet Gesundheitsdaten. Vor jedem produktiven Einsatz
mit echten Patientendaten: DSFA und MDR-Klassifizierung muessen abgeschlossen
sein (siehe `docs/anforderungen.md` Kapitel 12/13 und `DEFINITION_OF_DONE.md`,
Ebene 3). Waehrend der Entwicklung ausschliesslich synthetische Testdaten
verwenden.
