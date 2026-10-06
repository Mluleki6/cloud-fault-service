# Test Record — Teardown and Rebuild Check

Using the template from handbook §9.2.

| Field | Entry |
|---|---|
| Test ID and requirement | TR-02, handbook §7.1 teardown/rebuild check |
| Input/precondition | Project running via `docker compose up`, at least one ticket already persisted |
| Expected result | `docker compose down -v` removes everything, including the database volume; `docker compose up --build` recreates a working service from nothing |
| Actual result | Pass. `docker compose ps` was empty immediately after teardown. The rebuilt stack answered `GET /health` with `200`, and a fresh `POST /faults` returned `201` with ticket `FR-B5DDBEE0`, correlation id `180f6dbe-541f-4cdd-964c-876caccc2f89`, priority `P1` correctly derived from `severity: "high"` |
| Correlation/evidence reference | `180f6dbe-541f-4cdd-964c-876caccc2f89` (see `evidence/milestone4_teardown_verification_mluleki.md` for the full command sequence) |
| Pass/fail and defect link | Pass. No defect. |
| Retest result | Not needed, passed on first attempt. |
