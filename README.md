# Fault Reporting Service (4CPS501B Milestone 1-3 slice)

A small cloud-based event service: a user reports a faulty piece of
equipment or facility, the system validates it, assigns a ticket ID and
priority, persists it, attempts a downstream notification, and lets
the ticket be retrieved by ID. Built as the first working vertical
slice for the Cloud Computing Systems group project.

## Architecture

```
Client  ->  POST /faults  ->  validate  ->  assign ticket + priority
                                   |
                                   v
                          persist (Postgres / Cloud SQL)
                                   |
                                   v
                     notify maintenance contact (best-effort)
                                   |
                                   v
                  structured log (correlation_id ties it all together)

Client  ->  GET /faults/{ticket_id}  ->  retrieve persisted ticket
```

| Cloud role | This repo (local) | Managed cloud equivalent |
|---|---|---|
| API / function | FastAPI app in `app/`, run via Uvicorn | Cloud Run / Cloud Run functions |
| Relational state | Postgres container (`docker-compose.yml`) | Cloud SQL (Postgres) |
| Logging | Structured JSON to stdout (`app/logging_utils.py`) | Cloud Logging (auto-ingests stdout JSON) |
| Notification | Stub in `app/notify.py` | n8n webhook or Resend/SendGrid API call |
| Secrets | `.env` (never committed) | Secret Manager / Cloud Run env vars |

Local dev also defaults to SQLite (zero setup) when `DATABASE_URL` is
unset, so the test suite runs without Docker or Postgres.

## Prerequisites

- Python 3.11+ and pip, **or** Docker + Docker Compose
- (For Cloud Run deployment) `gcloud` CLI, authenticated, with an
  approved billing-enabled project

## Run locally (Docker Compose — recommended)

```bash
docker compose up --build
# API available at http://localhost:8080
```

Teardown:

```bash
docker compose down -v   # -v also removes the Postgres volume
```

## Run locally (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run the tests

```bash
pip install -r requirements.txt
pytest -v
```

This exercises every evidence category the handbook requires: normal
submission, retrieval, invalid input (missing field, bad severity),
a simulated dependency failure (`DB_FORCE_FAILURE=1`), and a
notification degradation case (`NOTIFY_FORCE_FAILURE=1`) that proves
the ticket is still persisted even when the downstream notification
fails.

> Note: this code was written and syntax-checked (`python -m py_compile`)
> in an environment without package-registry access, so the test suite
> itself has not yet been executed end-to-end. Run `pytest -v` as your
> first step and paste back any failures — they're most likely to be
> minor version-compatibility issues with the pinned FastAPI/Pydantic/
> SQLAlchemy versions in `requirements.txt`, not logic errors.

## API examples

Submit a valid report:

```bash
curl -X POST http://localhost:8080/faults \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": "LAB-014",
    "location": "Science Building, Room 214",
    "description": "Projector will not power on.",
    "severity": "high",
    "reporter_id": "STU-2026-001"
  }'
```

Retrieve it:

```bash
curl http://localhost:8080/faults/FR-XXXXXXXX
```

Simulate the dependency-failure case:

```bash
DB_FORCE_FAILURE=1 docker compose up
```

## Deploy to Cloud Run

One-time setup (creates the Cloud SQL instance, runner service account,
and stores the database credential in Secret Manager — see
`architecture/cost-worksheet.md` before running, this creates billable
resources):

```bash
GCP_PROJECT=your-project-id ./scripts/provision_gcp.sh
```

Then deploy (repeatable, e.g. after each code change):

```bash
GCP_PROJECT=your-project-id \
SQL_CONNECTION_NAME=your-project-id:africa-south1:fault-service-db \
./scripts/deploy_gcp.sh
```

Tear down after capturing evidence (also printed at the end of every
deploy):

```bash
gcloud run services delete fault-reporting-service --region africa-south1
gcloud sql instances delete fault-service-db
```

## Repository map

```
app/                  application source (validation, processing, persistence, notify, API)
tests/                pytest unit + component tests
architecture/          event contract, decision records
scripts/               deployment script
evidence/               (fill in during Milestone 3/4 with logs/screenshots per milestone)
docker-compose.yml     local distributed stack
Dockerfile             container build for Cloud Run / local Docker
.env.example           documented config keys -- copy to .env, never commit .env
```

## Known limitations (state these in the report, don't hide them)

- No duplicate-submission detection (idempotency) beyond ticket-ID
  uniqueness — out of scope for the MVP.
- Notification is a stub; wire it to a real n8n webhook or email API
  before the final Milestone 4 demonstration.
- No authentication/authorization layer yet — add before treating this
  as anything beyond a course prototype.
