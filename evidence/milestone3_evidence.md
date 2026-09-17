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

- **Notifications** remain a stub (`app/notify.py`) by design for this
  milestone — no external email/webhook account is required to run or grade
  the slice. Swappable later for a real Resend/SendGrid call or n8n webhook.
- **No authentication layer** — out of scope for a course prototype; would be
  needed before any real deployment.
- **No duplicate-submission detection** — out of scope for the MVP beyond
  ticket-ID uniqueness.
