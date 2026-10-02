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
| Elevation of privilege | **Updated 2026-10-02** — one privilege boundary now exists: holding `MAINTENANCE_API_KEY` lets a caller change a ticket's status, which a reporter cannot do | See the dedicated section below | Mitigated, with a named limitation |

## Reporter → Maintenance status update (`PATCH /faults/{ticket_id}/status`)

Added 2026-10-02, see [decisions/0002-maintenance-status-updates.md](decisions/0002-maintenance-status-updates.md).
This is the one place in the system with any access distinction at all,
so it gets its own table rather than a single row.

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Elevation of privilege | A reporter (or anyone) tries to change ticket status without the key | Request is refused with `403` unless `X-Maintenance-Key` matches `MAINTENANCE_API_KEY` exactly | Mitigated |
| Elevation of privilege | `MAINTENANCE_API_KEY` is never configured (e.g. forgotten in a deploy) | Fails closed: every request is refused, there is no default-open behaviour if the key is unset | Mitigated by design |
| Tampering | A timing attack on the key comparison, guessing the key one character at a time via response-time differences | `hmac.compare_digest` used for the comparison instead of `==`, which is not constant-time | Mitigated |
| Information disclosure | `MAINTENANCE_API_KEY` as a secret, anyone who has it can change any ticket's status | Read from the environment only, same handling as `DATABASE_URL`; confirmed absent from the repository by the same `detect-secrets` scan covering every other credential (see `architecture/final-test-set.md`) | Mitigated |
| Repudiation | No way to tell *which* maintenance team member made a given status change, since the key is shared, not per-person | Every change is logged with `old_status`, `new_status`, `ticket_id`, and `correlation_id`, but not an individual's identity | **Accepted, named limitation** — this is the explicit trade-off of choosing a shared key over per-user accounts, documented in the decision record rather than hidden |
| Spoofing | Someone other than genuine maintenance staff obtains the key and impersonates them | No technical control beyond the key itself; this is identical in kind to any shared-secret system | **Accepted risk** — proportionate to a course prototype with synthetic data; would need real per-user accounts before any real deployment, exactly the thing this design deliberately avoided for now |

## API endpoint → Persistence (Postgres / Cloud SQL)

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Tampering | SQL injection via any field (e.g. `description`) | SQLAlchemy ORM with parameterised queries throughout `app/persistence.py`; no raw string-built SQL anywhere in the codebase | Mitigated |
| Information disclosure | Database credentials in transit or at rest | Local dev: `docker-compose.yml` uses a placeholder password (`changeme`) for the local-only Postgres container, never used outside the isolated Docker network. Cloud: `scripts/deploy_gcp.sh` requires `DATABASE_URL` to be injected from Secret Manager / environment at deploy time and explicitly comments "never commit real values" | Mitigated for the cloud path; **accepted risk** for the local placeholder (dev-only, not internet-reachable) |
| Denial of service | DB connection exhaustion or outage | Handled as a first-class case: `DB_FORCE_FAILURE` produces a clean `503` rather than a crash — see **Q3** evidence | Mitigated (graceful degradation, not prevention) |

## API endpoint → Notification (maintenance contact)

| Threat (STRIDE) | Description | Mitigation | Status |
|---|---|---|---|
| Tampering | A real webhook could be sent a malicious payload (header/template injection) | Only three fixed fields (`ticket_id`, `equipment_id`, `priority`) are ever sent, built server-side from validated data — no user-controlled field (e.g. `description`) reaches the webhook payload | Mitigated |
| Information disclosure — webhook URL as a secret | A real `NOTIFY_WEBHOOK_URL` lets anyone who has it post to the team's channel | Read from the environment only (`.env`, git-ignored); never hardcoded, logged, or committed — same handling as `DATABASE_URL` | Mitigated |
| Information disclosure — email API key | A real `NOTIFY_EMAIL_API_KEY` (Resend) lets anyone who has it send email as the configured sender | Read from the environment only, same handling as `DATABASE_URL` and `NOTIFY_WEBHOOK_URL`; confirmed a detect-secrets scan finds no API key anywhere in the repository (see `architecture/final-test-set.md`) | Mitigated |
| Information disclosure — recipient address | `NOTIFY_EMAIL_TO` is a real mailbox address once configured | Not synthetic data by nature, but it identifies a role mailbox (the maintenance team), not a real student or staff individual's personal address, consistent with the Milestone 1 synthetic-data boundary for reporter data | Accepted, by design |
| Denial of service (to the system, not the user) | A slow/unreachable notification endpoint could block the request | 5-second timeout (`httpx.post(..., timeout=5.0)`); failure is caught (`NotificationError`) and logged; never blocks or fails the primary request — verified against a real endpoint returning both success and `500` — see `evidence/milestone3_evidence.md` | Mitigated |
| Information disclosure — ticket data sent externally | Ticket details are sent to whatever service the webhook points at | Only synthetic data is ever collected system-wide, so no real personal data is disclosed even when the channel is real | Mitigated by data-policy, not by code |

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

1. No authentication for reporting or retrieval (Milestone 1 decision, by
   design).
2. No rate limiting / DoS protection (out of scope for a course prototype).
3. Cloud Run deployed publicly (`--allow-unauthenticated`) — needed for a
   markable demo without a login flow; team should confirm this is
   acceptable before Milestone 4.
4. Local Postgres password is a placeholder, valid only inside the isolated
   Docker Compose network — never exposed to the internet.
5. Maintenance status updates (added 2026-10-02) use one shared secret for
   the whole team, not per-user accounts — no individual audit trail beyond
   the structured log, a deliberate trade-off recorded in
   `decisions/0002-maintenance-status-updates.md`, not a silent gap.

None of these are silent gaps — each is either an explicit product
exclusion from Milestone 1 or a documented, reasoned trade-off for a
short-lived course prototype with synthetic data only.
