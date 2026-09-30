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
| Notification | `app/notify.py` -- real webhook if `NOTIFY_WEBHOOK_URL` is set, zero-dependency stub otherwise | n8n webhook, Discord/Slack webhook, or Resend/SendGrid API call |
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
fails. All 17 tests pass as of the last run recorded in
`evidence/milestone3_evidence.md`.

## Reproduce the full evidence pack

Once the stack is running (`docker compose up --build -d`), run every
Milestone 3 scenario in one go and print the results:

```bash
bash scripts/smoke_test.sh
```

To trace one request end-to-end through the structured logs (the
correlation-ID requirement, **Q4**): copy the `correlation_id` from any
response, then:

```bash
docker compose logs app | grep <correlation_id>
```

You should see one JSON line per stage that request passed through
(e.g. `accepted` → `notified` or `notify_failed` → `persisted`), all
sharing the same ID.

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
app/                    application source (validation, processing, persistence, notify, API)
tests/                  pytest unit + component tests
architecture/           event contract, diagrams, decision records, interface
                        contracts, threat checklist, cost worksheet, failure
                        table, Milestone 3 integration plan
scripts/                provision_gcp.sh, deploy_gcp.sh, smoke_test.sh
evidence/               milestone3_evidence.md -- captured evidence pack,
                        reproducible on demand with scripts/smoke_test.sh
docker-compose.yml      local distributed stack
Dockerfile              container build for Cloud Run / local Docker
.env.example            documented config keys -- copy to .env, never commit .env
```

## Milestone 3 reproduction checklist (handbook §6.2 / §6.5)

Required: at least two team members must independently reproduce this
slice. If you are the second (or third, etc.) person doing this, follow
these steps from a clean clone with no help from whoever set it up
originally, then add your result to `evidence/milestone3_evidence.md`:

1. `git clone` this repository fresh.
2. `docker compose up --build -d` -- no other setup should be needed.
3. `bash scripts/smoke_test.sh` -- confirm every scenario matches what's
   already recorded in `evidence/milestone3_evidence.md`.
4. Pick one `correlation_id` from the output and trace it through
   `docker compose logs app | grep <correlation_id>`.
5. Note anything that didn't work, wasn't clear, or needed an
   undocumented step -- that's exactly what this check is for. Record it
   as a new entry in `architecture/decisions/` if it changes a prior
   decision, or as a note in `evidence/milestone3_evidence.md` either way.

## Real notifications (optional)

Set `NOTIFY_WEBHOOK_URL` (see `.env.example`) to have the notification
step actually POST to a webhook instead of the zero-dependency stub.
Any webhook receiver works -- the easiest zero-cost option is a
Discord server webhook (Server Settings -> Integrations -> Webhooks ->
New Webhook -> Copy URL), set alongside `NOTIFY_WEBHOOK_FORMAT=discord`.
Leave `NOTIFY_WEBHOOK_URL` unset to keep the original stub behaviour.

A failure of the real webhook still degrades exactly like the stub's
simulated failure did: the ticket is persisted, `notified` comes back
`false`, and the reason is logged (`fault_report.notify_failed`) --
verified against a live endpoint returning both 2xx and 5xx responses.

## Known limitations (state these in the report, don't hide them)

- No duplicate-submission detection (idempotency) beyond ticket-ID
  uniqueness — out of scope for the MVP.
- No authentication/authorization layer yet — add before treating this
  as anything beyond a course prototype.
