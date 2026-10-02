# Final Test Set (handbook §7.1)

Milestone 4 requires a specific minimum test set before release: 3 normal
cases, 2 invalid-input cases, 1 dependency/service failure, 1 recovery or
degradation, 1 security/control check, and 1 teardown/rebuild check. This
document maps each requirement to real, captured evidence, run against
the live Docker Compose stack on 2026-10-02 unless otherwise dated.

## Normal cases (3 required)

| # | Case | Request | Result |
|---|---|---|---|
| 1 | A different valid value (high severity) | `equipment_id: LAB-014, severity: high` | `201`, `priority: P1`. See `evidence/milestone3_evidence.md` §E1. |
| 2 | Boundary-valid value (every text field at its minimum length) | `equipment_id: "AB1"` (3 chars), `location: "A1"` (2 chars), `description: "Fixit"` (5 chars), `reporter_id: "STU"` (3 chars), `severity: medium` | `201`, ticket `FR-B7D6BD7B`, `priority: P2`. All four length-3/2/5/3 minimums accepted exactly at the schema's documented boundary (`architecture/event-contract.json`). |
| 3 | Repeated user journey (same reporter, two separate reports) | Reporter `STU-2026-777` submitted two different equipment faults back to back | Two distinct ticket IDs (`FR-4A9928E7`, `FR-4040B621`), both independently retrievable by `GET`, confirming no state is shared or overwritten between a reporter's separate submissions. |

## Invalid-input cases (2 required)

| # | Case | Result |
|---|---|---|
| 1 | Missing required field (`equipment_id` omitted) | `400 invalid_request`, no ticket created. See `evidence/milestone3_evidence.md` §E4. |
| 2 | Disallowed value (`severity: "urgent"`, not one of low/medium/high) | `400 invalid_request`, no ticket created. See `evidence/milestone3_evidence.md` §E5. |

(A third invalid case, malformed/non-JSON body, is also covered in
`evidence/milestone3_evidence.md` §E5b and was a genuine bug found and
fixed during Milestone 3, beyond the handbook's minimum of two.)

## Dependency/service failure (1 required)

Database forced unavailable (`DB_FORCE_FAILURE=1`): `503
dependency_unavailable`, no ticket created, no partial write. See
`evidence/milestone3_evidence.md` §E6.

## Recovery or degradation (1 required)

Notification channel forced unavailable (`NOTIFY_FORCE_FAILURE=1`): `201
Created`, ticket persisted and retrievable, `notified: false`, failure
logged with reason. See `evidence/milestone3_evidence.md` §E7. Confirmed
a second time against a real network failure (a live endpoint returning
HTTP 500, not a simulated flag) in the "Real notification channel
evidence" section of the same file.

## Security/control check (1 required)

The handbook's example wording is "unauthorised action denied; secret
scan clean; least-privilege check." This system has no authentication by
explicit, documented design (Milestone 1 exclusion), so "unauthorised
action denied" does not apply in the usual sense. The other two parts of
this check were run for real:

**Secret scan.** Ran `detect-secrets scan` (a real static secret
scanner, not a manual read-through) against every file tracked by git:

```
$ detect-secrets scan $(git ls-files)
```

Two files flagged, three findings, all three the same thing:

| File | Line | What it is |
|---|---|---|
| `.env.example` | 5 | `DATABASE_URL=postgresql://faultservice:changeme@db:5432/faultservice` |
| `docker-compose.yml` | 10 | `POSTGRES_PASSWORD: changeme` |
| `docker-compose.yml` | 28 | Same `changeme` password, repeated in the app service's `DATABASE_URL` |

All three are the same intentional, documented placeholder password,
used only inside the isolated Docker Compose network, never reachable
from outside it, and explicitly named `changeme` so nobody mistakes it
for a real credential. This is the same finding already triaged in
`architecture/threat-checklist.md` under "Information disclosure,
secrets in transit or at rest." No real secret, API key, token, or
production credential was found anywhere in the repository. The actual
database credential for a cloud deployment is never hardcoded; it is
read from Secret Manager at deploy time (`scripts/deploy_gcp.sh`,
`scripts/provision_gcp.sh`), and `.env` itself is git-ignored.

**Least-privilege check.** The cloud runner service account created by
`scripts/provision_gcp.sh` is granted exactly three roles:
`roles/cloudsql.client`, `roles/secretmanager.secretAccessor`, and
`roles/logging.logWriter`. No owner, editor, or administrator role is
ever granted to a workload identity. This was a design decision from
Milestone 2, confirmed still accurate by rereading the provisioning
script for this check.

## Teardown/rebuild check (1 required)

Run for real on 2026-10-02, not merely described:

1. `docker compose down -v` while the stack was running. Confirmed
   output: both containers stopped and removed, the network removed,
   and critically, the named volume `cloud-fault-service_fault_db_data`
   removed, meaning all persisted data was genuinely destroyed, not
   just the containers.
2. `docker compose ps` immediately after: empty, nothing left running.
3. `docker compose up --build -d` from that completely clean state.
   Docker's own output shows the volume being freshly created
   ("Volume ... Creating"), not reused.
4. `GET /health` returned `200` within seconds of the rebuilt containers
   starting.
5. A fresh `POST /faults` returned `201` with a correctly derived
   priority (`severity: low` to `priority: P3`), proving the entire
   slice, not just the container, works immediately after a full
   teardown and rebuild from the repository instructions alone.

This directly satisfies §7.6's teardown/rebuild acceptance item: the
environment can be destroyed and recreated to a working minimum slice
without any manual repair step.
