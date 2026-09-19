# Cost Worksheet — Fault Reporting Service

> **Actual outcome (2026-09-17):** GCP billing verification did not clear
> in time and the billing account was unlinked before any resource was
> created — confirmed no Cloud SQL instance, no Cloud Run service, both
> required APIs left disabled throughout. **Actual cloud spend: $0.** The
> team proceeded on the Docker Compose stack per
> [decisions/0001-platform-and-stack.md](decisions/0001-platform-and-stack.md#update--2026-09-17).
> The estimate below is kept as the planning analysis that informed the
> teardown-discipline decisions in that ADR, not as a claim that these
> resources were actually run.

Estimated GCP cost for the primary deployment target (Cloud Run + Cloud SQL
+ Cloud Logging), scoped to the actual workload: a short-lived course
prototype exercised only during milestone evidence capture, not a
continuously-running production service.

> **Verify before submitting.** GCP pricing and free-tier terms change over
> time and by region. Confirm current figures with the
> [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
> under region `africa-south1` (or your team's chosen region) before the
> final report — the numbers below are planning estimates, not quotes.

## Workload assumptions

- Evidence-capture sessions only: a few hours of active use per milestone,
  not 24/7 operation.
- Single Cloud Run service, single Cloud SQL instance (smallest tier),
  minimal request volume (tens–low hundreds of requests per session).
- No real user traffic outside the team and the lecturer's review.

## Per-service estimate

| Service | Free tier (approx.) | Course workload | Estimated cost if run continuously | Estimated actual cost (with teardown discipline) |
|---|---|---|---|---|
| **Cloud Run** | ~2M requests/month, 360k GB-seconds memory, 180k vCPU-seconds free per month | Low hundreds of requests total across all milestones | Within free tier | **$0** |
| **Cloud SQL** (Postgres, smallest instance, e.g. `db-f1-micro`) | No ongoing free tier (only initial trial credit) | Instance need only run during active evidence-capture windows | ~$7–10/month if left running continuously | **Low single-digit $ per milestone** if stopped between sessions; **$0** if only spun up for the capture window and deleted after |
| **Cloud Logging** | 50 GiB/project/month free | Structured JSON logs from a handful of test sessions — well under 1 GiB total | Within free tier | **$0** |
| **Cloud SQL storage** | N/A | Minimal (a handful of ticket rows) | ~$0.02–0.05/month for a few hundred MB | **Negligible**, but not zero while the instance/volume exists |

## Total estimate

- **With active teardown discipline** (stop/delete Cloud SQL between
  sessions, per the ADR's weekly-inventory commitment): **effectively $0
  across the whole module**, modulo a few cents of storage if a volume is
  left provisioned between sessions.
- **Worst case** (Cloud SQL instance left running continuously for the
  ~8-week module): roughly **$7–10 per calendar month** it's left up,
  dominated entirely by the Cloud SQL compute charge — Cloud Run and
  Logging stay within free tier at this workload regardless.

## Cost-control actions (tie back to the ADR's non-negotiable constraint)

1. **Stop, don't just leave, Cloud SQL** between evidence-capture sessions —
   `gcloud sql instances patch <instance> --activation-policy=NEVER`, or
   delete and recreate from a stored schema if state doesn't need to
   persist between milestones.
2. **Delete the Cloud Run service** after each milestone's evidence is
   captured — `scripts/deploy_gcp.sh` prints the exact teardown command on
   every deploy.
3. **Weekly resource inventory** — `gcloud run services list` and
   `gcloud sql instances list` — to catch anything left running by
   accident, per the ADR.
4. **Prefer the Docker Compose fallback for iterative local development**
   and only deploy to GCP when cloud-specific evidence is actually needed
   (e.g. Cloud Logging screenshots, Cloud Run URL demo) — this is the
   entire reason the ADR keeps Docker Compose as a first-class path rather
   than a last resort.

## Fallback path cost

The Docker Compose stack (`docker-compose.yml`) runs entirely on team
members' own machines — **$0 cloud cost**, at the expense of not having a
real Cloud Logging / Cloud Run artifact to screenshot for the report. If
GCP billing approval is delayed past the Milestone 2 deadline, this is the
documented zero-cost path per
[decisions/0001-platform-and-stack.md](decisions/0001-platform-and-stack.md).
