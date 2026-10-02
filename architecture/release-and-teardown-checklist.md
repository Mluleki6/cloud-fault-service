# Release and Teardown Checklist (handbook §7.6)

Self-assessed against every item in the handbook's checklist, with the
real check behind each line, not just a tick.

| Item | Status | Evidence |
|---|---|---|
| Final commit/tag recorded and report points to it | Done | Commit `188bd33` on `master`, https://github.com/Mluleki6/cloud-fault-service. The final report should name this commit as the one demonstrated. |
| Tests pass from a clean setup | Done | 22/22 pass after a full `docker compose down -v` and `docker compose up --build -d` from nothing. See `architecture/final-test-set.md`, "Teardown/rebuild check." |
| No unresolved placeholder, TODO, or populated secret file remains | Done | Searched `app/`, `tests/`, `scripts/` for `TODO`, `FIXME`, `XXX`: none found. No `.env` file exists in the working tree (only the safe `.env.example` template). |
| Repository secret scan and manual review completed | Done | `detect-secrets scan` run against every git-tracked file. Three findings, all the same documented placeholder password. See `architecture/final-test-set.md`, "Security/control check." |
| All cloud resources listed by service and region/project | Done, list is empty | Re-confirmed 2026-10-02: `gcloud billing projects describe project-a12689f2-b066-4b7a-812` returns `billingEnabled: false`, no billing account linked. No Cloud Run service, no Cloud SQL instance, no resource of any kind exists on this project. Nothing to list because nothing was ever created, consistent with `architecture/decisions/0001-platform-and-stack.md`'s update. |
| Evidence collected before deletion | Done | All Milestone 3 and 4 evidence was captured from the live running stack before any teardown. The teardown itself (`docker compose down -v`) was only run afterward, specifically to produce the teardown/rebuild evidence. |
| Chargeable resources deleted/stopped in dependency order | N/A, nothing chargeable exists | No GCP resource was ever created, so there is nothing to delete. If a GCP deployment happens later, the order is: Cloud Run service first (`gcloud run services delete`), then Cloud SQL instance (`gcloud sql instances delete`), as already printed at the end of `scripts/deploy_gcp.sh`. |
| Budgets/billing checked after teardown; local volumes and containers removed as appropriate | Done | GCP billing re-checked, confirmed inactive (above). Local Docker volume and containers were fully removed with `docker compose down -v` as part of the teardown/rebuild check, then recreated clean. |
| One member independently verifies that no unintended resources remain | Open | This needs a second person to run `docker compose ps`, `docker volume ls`, and (if they have GCP access) `gcloud run services list` / `gcloud sql instances list` themselves, and confirm nothing unexpected is running. Not yet done by anyone other than the original developer. |

## What is genuinely still open

Only the last line. Every other item has been executed and checked for
real, not assumed. The independent verification is a short task, five
minutes, and does not require Docker or GCP access beyond what any
team member already has from the Milestone 3 reproduction. Whoever
does it should add their result as a new row in this table with their
name and the date, the same way the Milestone 3 reproductions were
recorded in `evidence/milestone3_evidence.md`.
