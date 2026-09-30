# Milestone 3 Evidence Pack

Captured against the Docker Compose stack (FastAPI app + Postgres 16), commit
state after fixing the `docker-compose.yml` force-failure env passthrough and
the FastAPI `lifespan` startup handler. Every log line shares a
`correlation_id` with its triggering request, per `app/logging_utils.py`.

## Test suite (17/17 passing)

```
$ pytest -v
tests/test_api.py::test_submit_valid_report_returns_ticket PASSED
tests/test_api.py::test_retrieve_existing_ticket PASSED
tests/test_api.py::test_repeated_valid_submission_creates_distinct_tickets PASSED
tests/test_api.py::test_submit_missing_field_rejected PASSED
tests/test_api.py::test_submit_invalid_severity_rejected PASSED
tests/test_api.py::test_invalid_submission_does_not_create_a_ticket PASSED
tests/test_api.py::test_retrieve_missing_ticket_returns_404 PASSED
tests/test_api.py::test_database_unavailable_returns_503 PASSED
tests/test_api.py::test_notification_failure_degrades_gracefully PASSED
tests/test_validation.py::test_valid_report_parses PASSED
tests/test_validation.py::test_missing_required_field_rejected PASSED
tests/test_validation.py::test_invalid_severity_rejected PASSED
tests/test_validation.py::test_malformed_equipment_id_rejected PASSED
tests/test_validation.py::test_equipment_id_is_normalised_to_uppercase PASSED
tests/test_validation.py::test_priority_derivation[high-P1] PASSED
tests/test_validation.py::test_priority_derivation[medium-P2] PASSED
tests/test_validation.py::test_priority_derivation[low-P3] PASSED
17 passed in 0.34s
```

## E1. Normal submission → 201 Created

Request:
```
POST /faults
{"equipment_id":"LAB-014","location":"Science Building, Room 214",
 "description":"Projector will not power on.","severity":"high",
 "reporter_id":"STU-2026-001"}
```

Response:
```json
{"ticket_id":"FR-EFE74FBE","correlation_id":"e432b920-730a-4186-865b-953364106193",
 "equipment_id":"LAB-014","location":"Science Building, Room 214",
 "description":"Projector will not power on.","severity":"high","priority":"P1",
 "status":"open","reporter_id":"STU-2026-001",
 "created_at":"2026-09-17T12:45:46.394626","notified":true}
```

Log:
```json
{"timestamp": "2026-09-17T12:45:46.394514+00:00", "event": "fault_report.accepted", "correlation_id": "e432b920-730a-4186-865b-953364106193", "equipment_id": "LAB-014"}
{"timestamp": "2026-09-17T12:45:46.405735+00:00", "event": "fault_report.notified", "correlation_id": "e432b920-730a-4186-865b-953364106193", "ticket_id": "FR-EFE74FBE"}
{"timestamp": "2026-09-17T12:45:46.405890+00:00", "event": "fault_report.persisted", "correlation_id": "e432b920-730a-4186-865b-953364106193", "ticket_id": "FR-EFE74FBE", "priority": "P1"}
```

## E2. Retrieval by ticket ID → 200 OK

`GET /faults/FR-EFE74FBE` returns the same record persisted above.

Log:
```json
{"timestamp": "2026-09-17T12:45:46.584426+00:00", "event": "fault_report.retrieved", "correlation_id": "c42d4d14-fab4-45ad-af7a-0f468c10bb72", "ticket_id": "FR-EFE74FBE"}
```

## E3. Retrieval of unknown ticket → 404 Not Found

```
GET /faults/FR-DOESNOTEXIST
→ 404
{"detail":{"error":"not_found","detail":"No ticket found for id FR-DOESNOTEXIST","correlation_id":"cad5557c-8b45-4348-ad42-c398dce8dd8a"}}
```
```json
{"timestamp": "2026-09-17T12:45:46.638973+00:00", "event": "fault_report.not_found", "correlation_id": "cad5557c-8b45-4348-ad42-c398dce8dd8a", "ticket_id": "FR-DOESNOTEXIST"}
```

## E4. Invalid input — missing required field → 400 Bad Request

```
POST /faults  (equipment_id omitted)
→ 400
{"detail":{"error":"invalid_request","detail":"One or more fields failed validation.",
 "correlation_id":"5650e3da-88ff-4f88-b353-054c9be35a6a",
 "errors":[{"loc":["equipment_id"],"msg":"Field required","type":"missing"}]}}
```
```json
{"timestamp": "2026-09-17T12:45:46.722993+00:00", "event": "fault_report.rejected", "correlation_id": "5650e3da-88ff-4f88-b353-054c9be35a6a", "reason": "validation_error", "errors": [{"loc": ["equipment_id"], "msg": "Field required", "type": "missing"}]}
```

## E5. Invalid input — bad severity enum → 400 Bad Request

```
POST /faults  (severity: "urgent")
→ 400
{"detail":{"error":"invalid_request","detail":"One or more fields failed validation.",
 "correlation_id":"670ceecb-72eb-4f46-bc43-fd015f17c08c",
 "errors":[{"loc":["severity"],"msg":"Input should be 'low', 'medium' or 'high'","type":"enum"}]}}
```
```json
{"timestamp": "2026-09-17T12:45:46.787403+00:00", "event": "fault_report.rejected", "correlation_id": "670ceecb-72eb-4f46-bc43-fd015f17c08c", "reason": "validation_error", "errors": [{"loc": ["severity"], "msg": "Input should be 'low', 'medium' or 'high'", "type": "enum"}]}
```

## E6. Dependency failure — datastore unavailable → 503

Run with `DB_FORCE_FAILURE=1 docker compose up -d app`:

```
POST /faults
→ 503
{"detail":{"error":"dependency_unavailable","detail":"The datastore is currently unavailable. Please retry shortly.","correlation_id":"8b9e1860-a298-4e84-954f-12217cb26774"}}
```
```json
{"timestamp": "2026-09-17T12:45:56.136033+00:00", "event": "fault_report.accepted", "correlation_id": "8b9e1860-a298-4e84-954f-12217cb26774", "equipment_id": "HVAC-9"}
{"timestamp": "2026-09-17T12:45:56.136288+00:00", "event": "fault_report.db_unavailable", "correlation_id": "8b9e1860-a298-4e84-954f-12217cb26774", "ticket_id": "FR-2F91D407"}
```

No ticket is persisted or returned to the client in this case — the request
fails cleanly before the persistence step.

## E7. Notification degradation — ticket still persists → 201

Run with `NOTIFY_FORCE_FAILURE=1 docker compose up -d app` (DB healthy):

```
POST /faults
→ 201
{"ticket_id":"FR-91E1CE48","correlation_id":"d17545b4-d4ba-4399-ba12-bc03c05938a0",
 ...,"notified":false}
```
```json
{"timestamp": "2026-09-17T12:46:05.347854+00:00", "event": "fault_report.accepted", "correlation_id": "d17545b4-d4ba-4399-ba12-bc03c05938a0", "equipment_id": "AC-203"}
{"timestamp": "2026-09-17T12:46:05.360480+00:00", "event": "fault_report.notify_failed", "correlation_id": "d17545b4-d4ba-4399-ba12-bc03c05938a0", "ticket_id": "FR-91E1CE48", "reason": "Simulated notification service outage"}
{"timestamp": "2026-09-17T12:46:05.360597+00:00", "event": "fault_report.persisted", "correlation_id": "d17545b4-d4ba-4399-ba12-bc03c05938a0", "ticket_id": "FR-91E1CE48", "priority": "P3"}
```

This proves the core resilience requirement: a downstream notification
failure is logged and does not block or corrupt the primary transaction —
the ticket is still created and retrievable, just with `notified: false`.

## Known scope decisions (confirmed, not defects)

- **Notifications** support a real webhook (`NOTIFY_WEBHOOK_URL`, added
  2026-09-30) with the original zero-dependency stub kept as the default
  when it's unset — no external account is required to run or grade the
  slice unless a real channel is deliberately configured. See "Real
  notification channel evidence" below for the live-network verification.
- **No authentication layer** — out of scope for a course prototype; would be
  needed before any real deployment.
- **No duplicate-submission detection** — out of scope for the MVP beyond
  ticket-ID uniqueness.

## Real notification channel evidence (2026-09-30)

`app/notify.py` was extended so `NOTIFY_WEBHOOK_URL` (optional) makes a
real outbound HTTP call instead of the no-op stub. Verified against the
Docker stack after a full image rebuild (`docker compose up --build -d`),
using a public echo endpoint so no real credentials are needed to prove
the mechanism works:

**Success** — `NOTIFY_WEBHOOK_URL=https://httpbin.org/post`:
```
POST /faults -> 201, "notified": true
log: fault_report.accepted -> fault_report.notified -> fault_report.persisted
```

**Failure (real HTTP 500, not simulated)** — `NOTIFY_WEBHOOK_URL=https://httpbin.org/status/500`:
```
POST /faults -> 201, "notified": false  (ticket still persisted)
log: fault_report.notify_failed, reason: "Webhook call failed: Server error
     '500 INTERNAL SERVER ERROR' for url 'https://httpbin.org/status/500'"
```

This is a second, independent confirmation of the same degrade-gracefully
property as `NOTIFY_FORCE_FAILURE` (§E7 above) — this time against a real
network failure rather than a simulated one. 22/22 tests pass, including
5 new unit tests in `tests/test_notify.py` covering the stub default,
successful webhook post, Discord payload formatting, and both failure
modes (connection error and non-2xx response), all with the HTTP call
mocked so the test suite makes no real network requests.

## Data & Observability Verification — Mzameni Nkosi (2026-09-30)

As the Data & Observability Lead, I independently reproduced the
Milestone 3 service on Ubuntu 24.04.4 LTS using Docker Desktop.

### Environment

- Operating system: Ubuntu 24.04.4 LTS
- Docker Desktop: 4.93.0
- Application: FastAPI Fault Reporting Service
- Database: PostgreSQL 16
- API documentation: http://localhost:8080/docs

### QA Test 1 — Valid fault submission

A valid POST request was submitted to `/faults`.

Result: **HTTP 201 Created**

Ticket ID: `FR-8330B873`

Correlation ID: `4b5a7f31-6236-4605-9d89-4d3b9189c104`

The response contained the expected ticket ID, correlation ID, severity,
priority P1, open status, and notification result.

### QA Test 2 — Retrieve submitted fault

The ticket was retrieved using:

`GET /faults/FR-8330B873`

Result: **HTTP 200 OK**

The returned record matched the submitted fault information.

### QA Test 3 — Invalid request: missing reporter_id

A request without the required `reporter_id` field was submitted.

Result: **HTTP 400 Bad Request**

The service rejected the request rather than accepting incomplete data.

### QA Test 4 — Invalid JSON

A malformed JSON request was submitted with a missing comma.

Result: **HTTP 400 Bad Request**

The service rejected the malformed request.

### QA observations

The independent reproduction confirmed that the service can be started
locally, accepts valid fault reports, retrieves persisted tickets, and
rejects invalid requests.

During reproduction, an archive extraction issue was identified where
application filenames contained literal backslashes. The application
directory was corrected before rebuilding the Docker image.

The API also initially rejected a test request because `reporter_id` was
required. This confirmed that the validation requirement is enforced.

Evidence for the successful POST and GET responses was captured as
screenshots during the independent QA test.



## Data & Observability Contribution — Mzameni Nkosi (2026-09-30)

Role: Data & Observability Lead

Responsibilities completed:

- Reviewed the data flow for fault report submission and retrieval.
- Verified that fault reports are persisted and can be retrieved using the ticket ID.
- Reviewed structured logging to ensure important system events are recorded.
- Verified that correlation IDs allow tracing of a request across acceptance,
  notification and persistence stages.

Evidence reviewed:

- `app/persistence.py` for database persistence handling.
- `app/logging_utils.py` for structured JSON logging and correlation IDs.
- Milestone 3 evidence showing accepted, rejected, persisted and failed events
  linked through correlation IDs.

The contribution supports system observability by ensuring that stored data,
application events and request tracing can be verified during testing and
demonstration.


