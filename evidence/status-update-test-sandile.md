# Test: maintenance staff can update a ticket's status

**Tester:** Sandile Luthuli
**Date:** 2026-10-06
**Ticket:** FR-32B98B3E (LAB-014, Projector will not power on, severity medium, priority P2)

## Steps and results

| # | Action | Expected | Actual |
|---|--------|----------|--------|
| 1 | Update status to In progress with the correct maintenance key | Accepted (200) | Accepted: open -> in_progress |
| 2 | Update status with a wrong key | Refused (403) | Refused (403) |
| 3 | Update status to Resolved with the correct maintenance key | Accepted (200) | Accepted: in_progress -> resolved |
| 4 | Look up the ticket | Status shows resolved | Status shows resolved |

## Evidence

App logs show `fault_report.status_updated` events for each successful change
and `PATCH /faults/FR-32B98B3E/status HTTP/1.1 200 OK` responses.

## Notes

The first attempts were refused with 403 because the key in `.env` did not match
the key typed into the form. After setting a known key, the lifecycle
open -> in progress -> resolved worked as expected.

Result: PASS
