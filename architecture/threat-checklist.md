# Threat Checklist — Fault Reporting Service

STRIDE-based review of each component in [architecture-diagram.md](architecture-diagram.md),
scoped to what this system actually does: accept, validate, price, persist,
notify, and log a synthetic fault report. Written for the Milestone 2
"threat checklist" deliverable.

Severity is rated for **this course prototype's actual exposure** (synthetic
data only, no real personal information, short-lived deployment with
teardown discipline) — not for a hypothetical production rollout.

## Reporter → API endpoint

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Spoofing | No authentication — anyone reaching the endpoint can submit as any `reporter_id` | Explicit Milestone 1 exclusion; only synthetic IDs are ever accepted/stored, so impersonation has no real-world consequence | **Accepted risk** — documented, not mitigated |
| Tampering | Malformed/oversized/malicious payload | Pydantic schema enforces type, length, and format (`equipment_id` regex, enum for `severity`) before any processing | Mitigated |
| Repudiation | Reporter denies having submitted a report | Every accepted request is logged with a `correlation_id` and timestamp | Mitigated (logging only — no signing) |
| Information disclosure | Reporter fields could carry real personal data despite the synthetic-ID assumption | No format check *forces* synthetic data; this is a policy/process control, not a code control | **Accepted risk** — team must enforce via test-data discipline, per Milestone 1 §2 ethical boundary |
| Denial of service | Endpoint has no rate limiting; a flood of requests could exhaust DB connections | None at the application layer; Cloud Run's autoscaling absorbs some load, but this is not a real DoS mitigation | **Accepted risk** — out of scope for a course prototype; would need rate limiting before any real deployment |
| Elevation of privilege | N/A — no privilege levels exist in this system | — | N/A |

## API endpoint → Persistence (Postgres / Cloud SQL)

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Tampering | SQL injection via any field (e.g. `description`) | SQLAlchemy ORM with parameterised queries throughout `app/persistence.py`; no raw string-built SQL anywhere in the codebase | Mitigated |
| Information disclosure | Database credentials in transit or at rest | Local dev: `docker-compose.yml` uses a placeholder password (`changeme`) for the local-only Postgres container, never used outside the isolated Docker network. Cloud: `scripts/deploy_gcp.sh` requires `DATABASE_URL` to be injected from Secret Manager / environment at deploy time and explicitly comments "never commit real values" | Mitigated for the cloud path; **accepted risk** for the local placeholder (dev-only, not internet-reachable) |
| Denial of service | DB connection exhaustion or outage | Handled as a first-class case: `DB_FORCE_FAILURE` produces a clean `503` rather than a crash — see **Q3** evidence | Mitigated (graceful degradation, not prevention) |

## API endpoint → Notification (maintenance contact)

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Tampering | If wired to a real webhook/email API later, a malicious payload could be used for header/template injection | Currently a stub — no outbound call is made, so no real attack surface exists yet | N/A today; **must be re-reviewed** before wiring a real notification channel (see `app/notify.py` docstring) |
| Denial of service (to the system, not the user) | A slow/unreachable notification endpoint could block the request | Notification failure is caught (`NotificationError`) and logged; it never blocks or fails the primary request — see **Q3** evidence (`fault_report.notify_failed`) | Mitigated |
| Information disclosure | Ticket details sent to an external service once wired up | Only synthetic data is ever collected, so no real personal data would be disclosed even then | Mitigated by data-policy, not by code |

## Cross-cutting: logging

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Tampering / log injection | Attacker-controlled string fields (e.g. `description`) written into log lines | Log lines are built as a Python dict and serialised with `json.dumps` (`app/logging_utils.py`), not string-concatenated — no injection vector | Mitigated |
| Information disclosure | Logs could leak secrets or PII | No secrets are ever passed to `log_event`; no real PII is collected system-wide per the Milestone 1 ethical boundary | Mitigated by data-policy |

## Deployment / secrets

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Information disclosure | Secrets committed to the repository | `.env.example` ships only placeholder values; real `.env` is git-ignored; `scripts/deploy_gcp.sh` reads all secrets from the environment, never hardcodes them | Mitigated — satisfies **Q2** |
| Elevation of privilege | Cloud Run deployed with `--allow-unauthenticated` (see `scripts/deploy_gcp.sh`) | Deliberate — matches "no auth" being an explicit product exclusion, not an oversight. **Team decision point**: confirm this is acceptable for the Milestone 4 public demo, since it means the deployed endpoint is reachable by anyone | **Open decision** — confirm with team/lecturer before Milestone 4 |
| Elevation of privilege | Cloud Run service account scope | `scripts/deploy_gcp.sh` uses a dedicated `fault-service-runner` service account rather than the default compute service account, limiting blast radius if the container is compromised | Mitigated |

## Summary — accepted risks to state explicitly in the report

1. No authentication (Milestone 1 exclusion, by design).
2. No rate limiting / DoS protection (out of scope for a course prototype).
3. Cloud Run deployed publicly (`--allow-unauthenticated`) — needed for a
   markable demo without a login flow; team should confirm this is
   acceptable before Milestone 4.
4. Local Postgres password is a placeholder, valid only inside the isolated
   Docker Compose network — never exposed to the internet.

None of these are silent gaps — each is either an explicit product
exclusion from Milestone 1 or a documented, reasoned trade-off for a
short-lived course prototype with synthetic data only.
