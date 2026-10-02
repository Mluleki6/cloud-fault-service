# Final Repository Checklist (handbook §7.2) and Marking Evidence Map

## §7.2 checklist

| Required item | Status | Where |
|---|---|---|
| README with prerequisites, architecture summary, configuration variables, run/deploy, test and teardown steps | Done | `README.md` |
| Final architecture and event-flow diagrams | Done | `architecture/architecture-diagram.md`, `architecture/diagrams/event-flow.png` |
| Source code, modular functions, concise comments | Done | `app/` (validation in `schemas.py`, the one business rule in `processing.py`, persistence in `persistence.py`, notification in `notify.py`, logging in `logging_utils.py`, wiring in `main.py`) |
| Infrastructure/Compose templates, version pins | Done | `docker-compose.yml`, `Dockerfile` (`python:3.11-slim`), `requirements.txt` (every package pinned to an exact version) |
| Automated tests plus final test results | Done | `tests/`, 22 tests, results recorded in `evidence/milestone3_evidence.md` and `architecture/final-test-set.md` |
| Safe example configuration, no secret values | Done | `.env.example`; confirmed by a real secret scan, see `architecture/final-test-set.md` |
| Evidence pack indexed to requirements and rubric criteria | Done | See the index below |
| Decision log | Done | `architecture/decisions/0001-platform-and-stack.md` |
| Contribution record | Partial | See "What is genuinely incomplete" below |
| Peer review evidence | Not yet present | See "What is genuinely incomplete" below |
| Release tag/commit identifier used for the demonstration | Not yet tagged | No git tag exists yet. Tag the commit actually used for the Milestone 4 demonstration once the team has decided the final commit, do not tag early and then keep committing past it. |

## Evidence index (maps straight onto handbook §8's marking table)

| Rubric criterion | Where the evidence actually is |
|---|---|
| Problem definition and requirements | Milestone 1 proposal; `architecture/event-contract.json` |
| Architecture and justification | `architecture/architecture-diagram.md`, `architecture/decisions/0001-platform-and-stack.md`, `architecture/interface-contracts.md`, `architecture/failure-table.md` |
| Implementation and integration | `app/`, `docker-compose.yml`, three independent reproductions in `evidence/milestone3_evidence.md` |
| Testing, reliability and observability | `tests/` (22 passing), `architecture/final-test-set.md`, correlation ID traces throughout `evidence/milestone3_evidence.md` |
| Security, privacy and cost control | `architecture/threat-checklist.md`, `architecture/cost-worksheet.md`, the secret scan and least-privilege check in `architecture/final-test-set.md` |
| Technical report and repository quality | `README.md`, this checklist, the report itself |
| Demonstration and individual defence | Not a document, this is the live Milestone 4 session |
| Team process and contribution | Partial, see below |

## What is genuinely incomplete

Two things here are not finished, and I am not going to paper over them
with something that looks like evidence but is not.

**Contribution record.** The handbook's §9.3 template wants a dated
record of each member's tasks, commits, and hours. Right now every
commit in the repository's history is authored by one person, because
the rest of the team worked by running the packaged zip and sending
back screenshots rather than committing directly. That is real,
independent, traceable evidence of their work (recorded in
`evidence/milestone3_evidence.md`), but it is not the same thing as a
commit history showing five people's names. If the team wants a
stronger contribution record, the direct fix is for Andiswa Ngcobo,
Mzameni Nkosi, Sandile Luthuli, and Andiswa Anele Xulu to each make at
least one real commit before Milestone 4, even a small one such as
adding their own entry to this file. I can prepare a short, specific,
low-risk task for each of them if the team wants that.

**Peer review evidence.** The team charter's own review rule says no
change merges without another member's review. That has not happened
yet, since there has only been one contributor pushing commits. This
needs the same fix as above: once more than one person is committing,
reviews between them become possible and should be recorded, for
example as comments on commits or a short note in this file.

Both of these are team coordination gaps, not technical ones. I can
build the task, but I cannot make four other people pick it up.
