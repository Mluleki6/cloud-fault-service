# Milestone 4 Demonstration Script (handbook §7.4)

A script to prepare from, not a substitute for actually knowing the
system. Whoever presents should be comfortable deviating from this if
a question interrupts, since the handbook's individual defence assumes
real understanding, not a memorised sequence. Timing follows §7.4
exactly.

## 0:00 to 1:00, problem, user, event and success criterion

Say in your own words: students and staff at the University of Zululand
currently report equipment and facility faults informally, with no
ticket, no priority, and no way to confirm the report was received.
This service turns that into one event, `FaultReport`, that is
validated, assigned a priority and a ticket ID, persisted, and can be
retrieved later. Name one success criterion directly, for example F3,
the system derives a priority from severity rather than copying it from
the user.

## 1:00 to 2:30, architecture, platform route and one design decision

Show `architecture/architecture-diagram.md`'s event flow figure. State
the platform decision plainly: Docker Compose was chosen as the
delivered platform after a GCP billing account failed to verify in
time, with zero cloud resources ever created and zero cost incurred.
Point to `architecture/decisions/0001-platform-and-stack.md`'s "Update"
section as the record of that decision. Pick one other design decision
to speak to in more depth, for example why notification is best-effort
and never blocks ticket creation.

## 2:30 to 5:30, run valid cases, trace one correlation ID

Live, not a screenshot:

1. Open `http://localhost:8080/` (the plain form) or `/docs`.
2. Submit a fault report. Point out the returned `ticket_id`,
   `priority`, and `correlation_id`.
3. Run `docker compose logs app | grep <that correlation_id>` in a
   terminal, visible to the room. Show the three log lines
   (`accepted`, `notified`, `persisted`) sharing that one ID.
4. Look the ticket up again with `GET /faults/{ticket_id}`, showing the
   same record comes back from a completely separate request.

This is the single most important few minutes of the demo: it is the
one thing that proves the event actually travels through the system
rather than being four disconnected screenshots.

## 5:30 to 7:30, invalid and dependency-failure cases

1. Submit a report missing a required field, show the `400` and that
   no ticket was created.
2. Restart the app container with `DB_FORCE_FAILURE=1 docker compose up
   -d app`, submit a report, show the `503` and that nothing was
   written. Reset with `docker compose up -d app` afterward.
3. If time allows, also show the notification degradation case
   (`NOTIFY_FORCE_FAILURE=1`): the request still succeeds with
   `notified: false`, which is the more interesting failure because it
   proves one dependency failing does not take the whole request down.

## 7:30 to 8:30, security and privacy controls

State plainly, do not read the slide: no authentication, by explicit
documented design, not an oversight. Show `architecture/final-test-set.md`'s
secret scan result, three findings, all the same intentional local-only
placeholder password, no real secret anywhere in the repository. Mention
the least-privilege service account roles from `scripts/provision_gcp.sh`
even though no cloud resource was ever actually created from it.

## 8:30 to 9:15, cost, resource inventory, and control

State the actual number plainly: real cloud spend is zero, because
billing never cleared and no resource was ever created. Show the
`gcloud billing projects describe` output confirming `billingEnabled:
false` as of the last check. Reference `architecture/cost-worksheet.md`
for what the cost would have been if GCP had gone ahead, and the
discipline (stop/delete between sessions) that was planned for it.

## 9:15 to 10:00, limitations, teardown, release commit

State the three known limitations plainly: no authentication, no
duplicate-submission detection, no real cloud deployment. Show the
teardown and rebuild evidence from `architecture/final-test-set.md`,
a full `docker compose down -v` followed by a clean rebuild that still
works. Name the release commit, the one tagged for this demonstration
(see `architecture/release-and-teardown-checklist.md`).

## Before the actual day

- Decide who presents which section. The handbook's individual defence
  can ask any member about any part, so do not let one person own the
  whole script, everyone should be able to run at least the 2:30 to
  5:30 block themselves.
- Rehearse the correlation ID trace live at least once beforehand. It
  is the part most likely to go wrong in front of an audience if the
  exact grep command has not been typed before.
- Reset the database (`docker compose exec db psql -U faultservice -d
  faultservice -c "TRUNCATE TABLE tickets;"`) shortly before the real
  demonstration, so the ticket IDs shown are fresh, not leftover test
  data from rehearsal.
