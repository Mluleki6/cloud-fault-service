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

## Second-member reproduction (handbook §6.5)

**Reproduced by:** Mzameni Nkosi (Data & Observability Lead), via the
zero-GitHub package (`HOW_TO_TEST_THIS.txt`) sent directly, independent
of the primary development machine. Screenshots in
[milestone3/second-member-mzameni/](milestone3/second-member-mzameni/).

**What was submitted** (`04-post-faults-filled-body.png`):
```json
{
  "equipment_id": "PC-001",
  "location": "Computer Lab 1",
  "description": "Computer is not powering on",
  "severity": "high",
  "reporter_id": "STU-001"
}
```

**Resulting ticket, retrieved via a separate `GET /faults/{ticket_id}`
request** (`03-get-ticket-200-response.png`):
```json
{
  "ticket_id": "FR-8330B873",
  "correlation_id": "4b5a7f31-6236-4605-9d89-4d3b9189c104",
  "equipment_id": "PC-001",
  "location": "Computer Lab 1",
  "description": "Computer is not powering on",
  "severity": "high",
  "priority": "P1",
  "status": "open",
  "reporter_id": "STU-001",
  "created_at": "2026-09-30T20:05:19.572444",
  "notified": true
}
```
HTTP 200, at `http://localhost:8080/faults/FR-8330B873`, response header
`date: Wed, 30 Sep 2026 20:10:04 GMT` -- five minutes after the ticket's
`created_at`, consistent with an independent session (submit, then come
back and look it up), not a single scripted motion.

**What this proves:**
- The slice runs correctly on a second machine, from the README /
  `HOW_TO_TEST_THIS.txt` instructions alone, with no live help from the
  original developer -- satisfying §6.2's "create the environment from
  repository instructions on a clean machine."
- `severity: "high"` correctly derived `priority: "P1"` on an
  independent run (**F3**), not just in the primary developer's tests.
- A ticket persisted via `POST /faults` was retrieved via a *separate*
  `GET /faults/{ticket_id}` request (**F4**), reproduced independently.
- `reporter_id: "STU-001"` -- a synthetic ID, consistent with the
  Milestone 1 ethical/privacy boundary.
- `01-post-faults-form.png` and `02-response-schema-reference.png` show
  the Swagger UI before submission and the documented response schema;
  included for completeness even though they aren't live-call evidence.

This is the second of the two reproductions required by §6.5's
acceptance checklist ("at least two members have reproduced the
slice") -- the first being the original developer's own runs captured
throughout this document.

## Third and fourth member reproduction (handbook §6.5)

Two more team members reproduced the slice independently, each on their
own machine, going beyond the handbook's minimum of two reproductions.

**Andiswa Ngcobo (Architecture and Integration Lead).** Screenshots in
[milestone3/third-member-andiswa/](milestone3/third-member-andiswa/).
Her terminal shows the path `C:\Users\ngcob\Desktop\cloud computing\cloud-fault-service`,
confirming this ran on her own machine, not the original development
machine. She started the stack from the repository instructions alone:

```
PS C:\Users\ngcob\Desktop\cloud computing\cloud-fault-service> docker compose up --build -d
PS C:\Users\ngcob\Desktop\cloud computing\cloud-fault-service> docker compose ps
NAME                        STATUS                 PORTS
cloud-fault-service-app-1   Up 40 seconds          0.0.0.0:8080->8080/tcp
cloud-fault-service-db-1    Up 46 seconds (healthy) 0.0.0.0:5432->5432/tcp
PS ...> docker compose logs app
app-1  | INFO:     Started server process [1]
app-1  | INFO:     Waiting for application startup.
app-1  | INFO:     Application startup complete.
app-1  | INFO:     Uvicorn running on http://0.0.0.0:8080
```

She then submitted a report with three required fields missing
(`equipment_id`, `location`, `description`) and confirmed it was
rejected safely:
```json
{
  "detail": {
    "error": "invalid_request",
    "detail": "One or more fields failed validation.",
    "correlation_id": "7c5e4950-917b-4039-9a43-abbcbf7f950c",
    "errors": [
      {"loc": ["equipment_id"], "msg": "Field required", "type": "missing"},
      {"loc": ["location"], "msg": "Field required", "type": "missing"},
      {"loc": ["description"], "msg": "Field required", "type": "missing"}
    ]
  }
}
```
HTTP 400, response header `date: Fri, 02 Oct 2026 17:19:58 GMT`. This
proves the environment builds cleanly on a third machine and that the
invalid-input path works independently of the primary developer's own
tests.

**Sandile Luthuli (Function/Application Developer).** Screenshots in
[milestone3/fourth-member-sandile/](milestone3/fourth-member-sandile/).
He submitted and then retrieved his own ticket:
```json
{
  "ticket_id": "FR-44D2E1E5",
  "correlation_id": "84693f76-1b22-4917-9394-8b4da1aa604c",
  "equipment_id": "PRJ-007",
  "location": "Main Library, Room 3",
  "description": "Projector shows no signal.",
  "severity": "medium",
  "priority": "P2",
  "status": "open",
  "reporter_id": "STU-002",
  "created_at": "2026-10-02T17:32:39.832943",
  "notified": true
}
```
Retrieved via `GET /faults/FR-44D2E1E5`, HTTP 200, response header
`date: Fri, 02 Oct 2026 17:38:19 GMT`, roughly five and a half minutes
after `created_at`, again consistent with a genuine independent session
rather than one continuous action. `severity: "medium"` correctly
produced `priority: "P2"` on his machine, independent of every other
run of this same check.

Between Mzameni, Andiswa and Sandile, three of the five team members
have now independently reproduced this slice, each confirming a
different part of it: environment startup, the invalid-input path, and
the full valid submission and retrieval path.

The remaining two members, Mluleki Nkosinathi Mzelemu and Andiswa Anele
Xulu, also ran the stack and exercised the endpoints themselves. Their
runs are not written up with screenshots here, since the three above
already exceed the handbook's minimum of two independent reproductions
required by §6.5, and duplicating the same evidence five times over
would not add anything beyond what is already demonstrated.

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
