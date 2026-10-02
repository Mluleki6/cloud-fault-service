# Interface Contracts — Fault Reporting Service

Formal contract for every endpoint exposed inside the trust boundary. This
extends [event-contract.json](event-contract.json) (which covers the
`FaultReport` event payload) to the full HTTP interface, per the
Milestone 2 requirement for documented interface contracts.

## Conventions

- All request/response bodies are `application/json`.
- Every response — success or error — carries a `correlation_id` so a single
  request can be traced end-to-end through the structured logs (**Q4**).
- No endpoint requires per-user authentication (reporting and retrieval remain
  fully open, an explicit Milestone 1 decision).
- **Amended 2026-10-02** (see [decisions/0002-maintenance-status-updates.md](decisions/0002-maintenance-status-updates.md)):
  one endpoint, `PATCH /faults/{ticket_id}/status`, now mutates a ticket after
  creation, gated by a single shared secret rather than per-user accounts. This
  reverses the Milestone 1 proposal's "no status changes after creation"
  exclusion; the record above explains why and what it does not include.

## §5.3 template — per interface

The handbook's interface contract template (§5.3) asks for eight fields per
interface. Full detail on each is in the sections below; this table is the
compact, template-exact form for quick marking reference. `Owner` names the
role from [milestone3-integration-plan.md](milestone3-integration-plan.md)
that owns this code path, with the member named in the Milestone 1 team
charter.

| Field | `POST /faults` | `GET /faults/{ticket_id}` | `PATCH /faults/{ticket_id}/status` | `GET /health` |
|---|---|---|---|---|
| **Name** | SubmitFaultReport | RetrieveFaultReport | UpdateTicketStatus | HealthCheck |
| **Trigger/endpoint** | `POST /faults` | `GET /faults/{ticket_id}` | `PATCH /faults/{ticket_id}/status` | `GET /health` |
| **Input** | JSON body: `equipment_id`, `location`, `description`, `severity`, `reporter_id` (all required — see [event-contract.json](event-contract.json)) | Path param `ticket_id` (string) | Path param `ticket_id`; JSON body `{"status": "open"\|"in_progress"\|"resolved"}`; header `X-Maintenance-Key` | None |
| **Validation** | Pydantic schema: type, length bounds, `severity` enum, `equipment_id` format regex, normalised to uppercase | None beyond string path parsing — invalid/unknown IDs are a 404, not a validation error | `status` must be one of the enum values; `X-Maintenance-Key` must match `MAINTENANCE_API_KEY` exactly (constant-time comparison) | None |
| **Success output** | `201`, `FaultReportOut` body incl. `ticket_id`, `correlation_id`, derived `priority`, `notified` flag | `200`, same `FaultReportOut` shape as the original submission | `200`, same `FaultReportOut` shape with the updated `status` | `200`, `{"status":"ok"}` |
| **Failure output** | `400 invalid_request` (bad input, no ticket created); `503 dependency_unavailable` (DB down, no ticket created) — both carry `correlation_id` | `404 not_found`, carries `correlation_id` | `403 forbidden` (missing/wrong/unconfigured key); `404 not_found` (unknown ticket); `400 invalid_request` (bad status value) | None defined — process responding at all implies `200` |
| **Idempotency** | **Not idempotent.** Every valid submission creates a new `ticket_id`, even if the payload is identical to a prior request. Duplicate-submission detection is an explicit out-of-scope exclusion (Milestone 1 §2, `event-contract.json`'s `idempotency_note`) | Idempotent — read-only, same ticket returned for repeated calls with the same ID | Idempotent — setting the same status twice leaves the ticket in that status both times, no error on a no-op transition | Idempotent — stateless liveness check |
| **Owner** | Function/Application Developer — Sandile Luthuli | Data & Observability Lead — Mzameni Nkosi | Cloud Platform & Security Lead — Mluleki Nkosinathi Mzelemu | Cloud Platform & Security Lead — Mluleki Nkosinathi Mzelemu |

## GET /health

Liveness probe. Used by orchestrators (Docker healthcheck, Cloud Run
startup/liveness probes) to confirm the process is up.

| | |
|---|---|
| Auth | None |
| Request body | None |

**200 OK**
```json
{"status": "ok"}
```

No failure mode is defined for this endpoint — if the process can respond
at all, it returns `200`.

---

## POST /faults

Submit a new fault report. Implements **F1**–**F3**.

| | |
|---|---|
| Auth | None |
| Request body | `FaultReportIn` — see [event-contract.json](event-contract.json) |

**201 Created** — report accepted, ticket assigned and persisted.
```json
{
  "ticket_id": "FR-9F3A21B0",
  "correlation_id": "b6f0b6a2-...",
  "equipment_id": "LAB-014",
  "location": "Science Building, Room 214",
  "description": "Projector will not power on.",
  "severity": "high",
  "priority": "P1",
  "status": "open",
  "reporter_id": "STU-2026-001",
  "created_at": "2026-08-28T14:00:00Z",
  "notified": true
}
```
`notified` is `false` (not an error) if persistence succeeded but the
best-effort notification step failed — the request still returns `201`.
This is the contract's explicit statement of **Q3**'s non-blocking
dependency behaviour for the notification channel.

**400 Bad Request** — one or more fields failed validation. **No ticket is
created.** Implements **F2**.
```json
{
  "detail": {
    "error": "invalid_request",
    "detail": "One or more fields failed validation.",
    "correlation_id": "b6f0b6a2-...",
    "errors": [
      {"loc": ["severity"], "msg": "Input should be 'low', 'medium' or 'high'", "type": "enum"}
    ]
  }
}
```

**503 Service Unavailable** — the datastore dependency is unavailable.
**No ticket is created or returned.** Implements **Q3**'s "safe error, not a
crash or corrupted state" for the persistence dependency.
```json
{
  "detail": {
    "error": "dependency_unavailable",
    "detail": "The datastore is currently unavailable. Please retry shortly.",
    "correlation_id": "b6f0b6a2-..."
  }
}
```

---

## GET /faults/{ticket_id}

Retrieve a previously persisted ticket by ID. Implements **F4**.

| | |
|---|---|
| Auth | None |
| Path param | `ticket_id` — string, e.g. `FR-9F3A21B0` |
| Request body | None |

**200 OK** — same shape as the `POST /faults` success response.

**404 Not Found**
```json
{
  "detail": {
    "error": "not_found",
    "detail": "No ticket found for id FR-DOESNOTEXIST",
    "correlation_id": "b6f0b6a2-..."
  }
}
```

## PATCH /faults/{ticket_id}/status

Maintenance-only: move a ticket between `open`, `in_progress`, and
`resolved`. Added 2026-10-02, see
[decisions/0002-maintenance-status-updates.md](decisions/0002-maintenance-status-updates.md).

| | |
|---|---|
| Auth | Shared secret, `X-Maintenance-Key` header, must equal `MAINTENANCE_API_KEY` |
| Path param | `ticket_id` — string |
| Request body | `{"status": "open" \| "in_progress" \| "resolved"}` |

**200 OK** — same shape as `POST /faults`'s success response, with the
updated `status`.

**403 Forbidden** — missing key, wrong key, or `MAINTENANCE_API_KEY` not
configured at all (fails closed, never defaults to open access).
```json
{
  "detail": {
    "error": "forbidden",
    "detail": "A valid maintenance key is required to update ticket status.",
    "correlation_id": "b6f0b6a2-..."
  }
}
```

**404 Not Found** — same shape as `GET /faults/{ticket_id}`'s 404.

**400 Bad Request** — `status` is not one of the three allowed values,
caught by the same global malformed-request handler as every other body
validation error in this service, so it returns the same `invalid_request`
shape, not a generic framework error.

## Error catalogue

| `error` code | HTTP status | Meaning | Ticket created? |
|---|---|---|---|
| `invalid_request` | 400 | Request body failed schema validation | No |
| `not_found` | 404 | No ticket exists for the given `ticket_id` | N/A (read) |
| `dependency_unavailable` | 503 | Datastore unreachable at write time | No |
| `forbidden` | 403 | Missing, wrong, or unconfigured maintenance key on a status update | N/A (no change made) |

## Traceability

Every row in the error catalogue, and every success path, is backed by a
structured log line sharing the same `correlation_id` — see
`app/logging_utils.py` and the captured examples in
[evidence/milestone3_evidence.md](../evidence/milestone3_evidence.md).
