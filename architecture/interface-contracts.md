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
