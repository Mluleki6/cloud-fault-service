# Interface Contracts — Fault Reporting Service

Formal contract for every endpoint exposed inside the trust boundary. This
extends [event-contract.json](event-contract.json) (which covers the
`FaultReport` event payload) to the full HTTP interface, per the
Milestone 2 requirement for documented interface contracts.

## Conventions

- All request/response bodies are `application/json`.
- Every response — success or error — carries a `correlation_id` so a single
  request can be traced end-to-end through the structured logs (**Q4**).
- No endpoint requires authentication (explicit Milestone 1 exclusion).
- No endpoint mutates a ticket after creation (explicit Milestone 1
  exclusion — no status-update endpoint exists).

## §5.3 template — per interface

The handbook's interface contract template (§5.3) asks for eight fields per
interface. Full detail on each is in the sections below; this table is the
compact, template-exact form for quick marking reference. `Owner` names the
role from [milestone3-integration-plan.md](milestone3-integration-plan.md)
that owns this code path — the actual team member is still TBC pending the
team's role-allocation meeting.

| Field | `POST /faults` | `GET /faults/{ticket_id}` | `GET /health` |
|---|---|---|---|
| **Name** | SubmitFaultReport | RetrieveFaultReport | HealthCheck |
| **Trigger/endpoint** | `POST /faults` | `GET /faults/{ticket_id}` | `GET /health` |
| **Input** | JSON body: `equipment_id`, `location`, `description`, `severity`, `reporter_id` (all required — see [event-contract.json](event-contract.json)) | Path param `ticket_id` (string) | None |
| **Validation** | Pydantic schema: type, length bounds, `severity` enum, `equipment_id` format regex, normalised to uppercase | None beyond string path parsing — invalid/unknown IDs are a 404, not a validation error | None |
| **Success output** | `201`, `FaultReportOut` body incl. `ticket_id`, `correlation_id`, derived `priority`, `notified` flag | `200`, same `FaultReportOut` shape as the original submission | `200`, `{"status":"ok"}` |
| **Failure output** | `400 invalid_request` (bad input, no ticket created); `503 dependency_unavailable` (DB down, no ticket created) — both carry `correlation_id` | `404 not_found`, carries `correlation_id` | None defined — process responding at all implies `200` |
| **Idempotency** | **Not idempotent.** Every valid submission creates a new `ticket_id`, even if the payload is identical to a prior request. Duplicate-submission detection is an explicit out-of-scope exclusion (Milestone 1 §2, `event-contract.json`'s `idempotency_note`) | Idempotent — read-only, same ticket returned for repeated calls with the same ID | Idempotent — stateless liveness check |
| **Owner** | Function/application developer (member: TBC) | Data & observability lead (member: TBC) | Cloud platform & security lead (member: TBC) |

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

## Error catalogue

| `error` code | HTTP status | Meaning | Ticket created? |
|---|---|---|---|
| `invalid_request` | 400 | Request body failed schema validation | No |
| `not_found` | 404 | No ticket exists for the given `ticket_id` | N/A (read) |
| `dependency_unavailable` | 503 | Datastore unreachable at write time | No |

## Traceability

Every row in the error catalogue, and every success path, is backed by a
structured log line sharing the same `correlation_id` — see
`app/logging_utils.py` and the captured examples in
[evidence/milestone3_evidence.md](../evidence/milestone3_evidence.md).
