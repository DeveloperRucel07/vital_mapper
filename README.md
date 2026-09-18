# Vital Mapper

Vital Mapper is a privacy-focused, speech-assisted nursing documentation platform for clinical care environments. It transforms spoken nursing observations into structured, reviewable documentation while keeping healthcare professionals in control of every clinical decision.

The application supports the complete documentation workflow: recording audio, generating transcripts, extracting clinical information, reviewing and correcting AI-generated suggestions, approving documentation, and forwarding approved data to an external nursing monitoring system. Extracted information can include blood pressure, pulse, temperature, oxygen saturation, pain scores, fluid intake, mobility, orientation, falls, interventions, and patient reactions.

Safety and traceability are core principles. AI-generated values must remain grounded in the transcript and may not be invented or completed with defaults. Missing or uncertain information remains visible for manual review. Clinical data is transmitted only after explicit human approval. The system also supports audit logging, role-based access control, patient-level authorization, encrypted audio storage, and privacy-preserving patient references.

Vital Mapper uses local or on-premises speech recognition and language-model services. Approved nursing reports and vital measurements are sent through a versioned interoperability gateway. The monitoring system performs the authoritative FHIR, LOINC, and UCUM mapping, so internal field names do not need to match the external clinical data model.

## Features

- Speech recording and transcript persistence
- Local transcription with faster-whisper
- Local clinical extraction with Ollama
- Grounding checks that prevent unsupported clinical values
- Manual review, correction, and approval workflow
- Vital-sign mapping for blood pressure, pulse, temperature, SpO2, and pain
- Keycloak/OIDC authentication with server-side session handling
- Role-based and patient-level access control
- Encrypted audio storage and audit logging
- PostgreSQL persistence and Redis-backed sessions
- Docker Compose development environment

## Architecture

The backend follows Clean Architecture:

```text
src/vital_mapper/
|-- domain/          # Clinical entities and business rules
|-- application/     # Use cases and abstract ports
|-- infrastructure/  # Database, AI, security, and integration adapters
`-- interfaces/api/  # FastAPI routes and dependency wiring
```

External services are accessed through infrastructure adapters. Clinical data is never sent directly from the domain or application layers to an external system.

## Quick start with Docker

Create the local environment file and set the required secrets:

```bash
cp .env.example .env
docker compose up --build
```

Pull the Ollama model once after the containers are running:

```bash
docker compose exec ollama ollama pull llama3.1:8b-instruct
```

The application is then available at:

- Frontend: `http://localhost:4000`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

The interoperability gateway must be running separately at the address configured by `INTEROP_GATEWAY_URL`.

## Local development

Install the backend and development dependencies:

```bash
pip install -e ".[dev]" --break-system-packages
uvicorn vital_mapper.interfaces.api.main:app --reload
```

For frontend development:

```bash
cd frontend
npm install
npm run dev
```

## Quality checks

Run the complete backend quality gate before submitting changes:

```bash
pytest
ruff check src tests
ruff format --check src tests
mypy src
bandit -r src -ll
pip-audit
```

Never commit `.env` files, access tokens, passwords, certificates, patient data, or generated model/cache files.
