# Failure Table — Fault Reporting Service

Required Milestone 2 submission item (§5.6): *"Failure table: failure,
expected user behaviour, evidence and recovery/degradation."* One row per
designed failure scenario, each backed by evidence already captured in
[evidence/milestone3_evidence.md](../evidence/milestone3_evidence.md) and
reproducible via `scripts/smoke_test.sh`.

| # | Failure | Expected user behaviour | Evidence | Recovery / degradation |
|---|---|---|---|---|
| 1 | Datastore unavailable (`DB_FORCE_FAILURE=1`) | `503 Service Unavailable`, JSON body `{"error":"dependency_unavailable", "detail":"...retry shortly.", "correlation_id":...}`. No ticket ID is returned. | `evidence/milestone3_evidence.md` §E6 — log shows `fault_report.accepted` then `fault_report.db_unavailable`, same `correlation_id` | **Fails safely, no partial state.** No row is written (verified: the DB write happens strictly after the check). Client can retry once the dependency recovers; no manual cleanup needed since nothing was persisted. |
| 2 | Notification channel unavailable (`NOTIFY_FORCE_FAILURE=1`) | `201 Created` — request **succeeds**, ticket returned with `"notified": false`. | `evidence/milestone3_evidence.md` §E7 — log shows `fault_report.accepted` → `fault_report.notify_failed` → `fault_report.persisted`, same `correlation_id` | **Degrades gracefully, does not block the primary transaction.** Ticket is fully durable and retrievable; the failed notification is logged with a reason and could be retried/escalated out-of-band. This is the system's core resilience property: a best-effort dependency failing never corrupts or blocks the request. |
| 3 | Missing required field (e.g. `equipment_id` omitted) | `400 Bad Request`, `{"error":"invalid_request", ..., "errors":[{"loc":["equipment_id"],"msg":"Field required",...}]}` | `evidence/milestone3_evidence.md` §E4 | **No record created.** Client corrects the field and resubmits; no state to clean up. |
| 4 | Invalid enum value (`severity: "urgent"`) | `400 Bad Request` with the specific invalid field named in `errors` | `evidence/milestone3_evidence.md` §E5 | Same as above — reject before processing, no record created. |
| 5 | Malformed / non-JSON request body | `400 Bad Request` in the **same error shape** as every other rejection (`error`/`detail`/`correlation_id`) — not a generic framework error | `scripts/smoke_test.sh` §E5b; fixed in `app/main.py`'s `RequestValidationError` handler, which also logs `fault_report.rejected` (this previously bypassed logging entirely — see commit `966af72`) | No record created; client fixes the request body. |
| 6 | Retrieval of a non-existent ticket ID | `404 Not Found`, `{"error":"not_found", "detail":"No ticket found for id ...", "correlation_id":...}` | `evidence/milestone3_evidence.md` §E3 | Read-only path — nothing to recover; client checks the ID or accepts the ticket doesn't exist. |

## What every row demonstrates together

Every failure — whether a client mistake (rows 3–5), a missing resource
(row 6), or a real dependency outage (rows 1–2) — returns a **safe,
structured, correlation-ID-bearing response** and never leaves the system
in an inconsistent state (no orphaned tickets, no partial writes). Row 2 is
the one selected as *the* designed failure scenario for Milestone 3/4's
single required dependency-failure test, since it's the more interesting
case: not just "fail safely" but "succeed anyway, degraded."
