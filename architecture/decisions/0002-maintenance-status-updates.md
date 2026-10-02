# 0002, Maintenance Status Updates

## Status

Decided 2026-10-02. This amends explicit exclusions from the Milestone 1 proposal,
which stated that *"changes to the ticket after it has been created"*
and the *"in progress" and "resolved" ticket statuses* were out of
scope. This record exists so that reversal is traceable, not silent, per the ADR discipline already
used in [0001-platform-and-stack.md](0001-platform-and-stack.md).

## Decision

Add one new endpoint, `PATCH /faults/{ticket_id}/status`, that lets a
ticket move between `open`, `in_progress`, and `resolved`. Access is
gated by a single shared secret (`MAINTENANCE_API_KEY`) sent as an
`X-Maintenance-Key` header, compared with a constant-time comparison
(`hmac.compare_digest`). If the key is not configured at all, every
request to this endpoint is refused, there is no default-open state.

## Context

The reporter-facing side of the system was complete and tested, but
the maintenance side had a real, named gap: tickets could be created
and read, but their status could not be updated. A reporter therefore
had no way to know whether their fault was actually being worked on;
they could only see that it had been logged.

## Options considered

1. **Full user accounts with login, per-user roles, and a dashboard.**
   The most capable option, but the largest change by far: it needs a
   user/credential model, session handling, and a UI the team has not
   designed, tested, or defended. Explicitly declined twice before
   this decision was made, on the grounds that it would invalidate
   work the team had already tested and understood for Milestone 3.
2. **One shared secret key, no accounts.** Chosen. Distinguishes "the
   maintenance team" from "a reporter" without needing to know who,
   specifically, within that team made the change. Smallest change
   that still closes the actual gap.
3. **Do nothing and leave the status permanently "open".** Rejected
   because it was the thing actually being asked for: a reporter should not
   have to wait indefinitely with zero visibility into whether their
   fault is even being looked at.

## Consequences

- This is a real, although small, widening of scope beyond what
  Milestones 1 and 2 documented. The Milestone 1 proposal's exclusions
  list, and the "No endpoint mutates a ticket after creation" line
  in `architecture/interface-contracts.md`, are both now inaccurate
  unless updated, which this change does alongside this record.
- `MAINTENANCE_API_KEY` is a new secret to manage. It must never be
  committed, and is read from the environment only, same handling as
  `DATABASE_URL` and the notification credentials. See the updated
  `architecture/threat-checklist.md`.
- This is still not an authentication system. There is one shared key
  for "the maintenance team" as a whole, not per-person accounts, no
  audit trail of which individual made a given change beyond the
  structured log entry itself. That is a deliberate, named limitation,
  not an oversight, stated here so it does not need rediscovering.
- Every team member who already reproduced the slice for Milestone 3
  tested it before this endpoint existed. This change does not affect
  the reporter-facing submit/retrieve flow they already verified, but
  if asked about ticket status in the Milestone 4 defence, the honest
  answer is: added 2026-10-02, after their reproductions, verify
  it works by reading this record and `evidence/milestone3_evidence.md`.

## Evidence

- Code: `app/main.py` (`update_fault_status`), `app/schemas.py`
  (`TicketStatus`, `StatusUpdateIn`), `app/persistence.py`
  (`update_ticket_status`).
- Tests: `tests/test_api.py`, six new tests covering the correct-key
  success path, missing key, wrong key, unconfigured key, unknown
  ticket, and an invalid status value.
- Live verification against the real running stack: see
  `evidence/milestone3_evidence.md`, "Maintenance status update
  evidence."
