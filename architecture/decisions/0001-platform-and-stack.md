# 0001 — Platform and Application Stack

## Decision
Use Python (FastAPI) for the application, Postgres for persistence, and
target Google Cloud (Cloud Run + Cloud SQL + Cloud Logging) as the
primary deployment platform, with a Docker Compose stack as the
provider-neutral local/fallback environment (Handbook Option D, mapped
to Option E for the cloud target).

## Context
4CPS501B requires a small cloud-based event service, built and defended
by a five-person team within an eight-week window with hard two-week
milestone gates. The team needs a platform that (a) at least one member
already has real, defensible hands-on experience with, (b) does not
require complex IAM setup before the team can make progress, and (c)
has a genuine zero-cost local fallback in case cloud account approval
is delayed.

## Options considered
1. **AWS native serverless** (API Gateway + Lambda + DynamoDB) — closest
   to the course's primary case study, but no team member has hands-on
   AWS experience yet, and the handbook itself flags IAM complexity and
   incomplete teardown as the main risk for this route.
2. **Google Cloud** (Cloud Run + Cloud SQL + Cloud Logging) — one team
   member has real, working experience deploying to GCP on a prior
   project, which reduces onboarding risk and supports a stronger
   individual defence.
3. **LocalStack** — avoids billing risk entirely but adds emulation-gap
   risk and version/service-coverage churn.
4. **Docker Compose (provider-neutral)** — zero billing risk, but must
   be explicitly mapped to managed-service equivalents in the report.

## Rationale
Google Cloud is selected as the primary target because it converts
directly into working progress in week one rather than a week of
account/IAM setup, and because the team can lean on real prior
experience during the Milestone 2 architecture review and the
Milestone 4 individual defence. Docker Compose is kept as the
documented fallback so the team is not blocked if GCP billing approval
is delayed — the same application code runs unmodified against either
target; only `DATABASE_URL` and the deployment command change.

## Consequences
- The team must confirm GCP billing/project approval with the lecturer
  before Milestone 1 is due (6 Sept 2026).
- All cloud resources must be inventoried and torn down after each
  milestone's evidence is captured, per the handbook's non-negotiable
  constraints.
- If GCP access is not approved in time, the team proceeds on Docker
  Compose alone and states this limitation explicitly in the final
  report, per the handbook's guidance for Option D.

## Evidence
- Application code: `app/` (FastAPI, framework-agnostic business logic
  in `processing.py` / `validation` via `schemas.py`).
- Local/cloud persistence equivalence: `app/persistence.py`
  (`DATABASE_URL` swap between SQLite/Postgres/Cloud SQL).
- Local stack: `docker-compose.yml`.
- Cloud provisioning (one-time): `scripts/provision_gcp.sh`.
- Cloud deploy path (repeatable): `scripts/deploy_gcp.sh`.
