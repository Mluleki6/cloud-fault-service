# Milestone 4 UI/Dashboard Validation -- Andiswa Xulu

Date: 07 October 2026

## Objective
Test the actual web dashboard (http://localhost:8080/), not just the API
directly, covering client-side validation, server-side validation as
rendered in the UI, a normal submission/lookup, and the maintenance
status-update form end to end, with a direct database check to confirm
the UI's result is really persisted.

## Steps and results

1. **Blank-form submission.** Left every field empty and clicked
   "Submit report". The browser's own HTML5 validation blocked the
   request before it reached the server ("Please fill out this field").
   See `01-blank-form-client-validation.png`.

2. **Invalid Equipment ID.** Entered `Lab- 01` (contains a space).
   Submitted successfully past client-side validation, but the server
   rejected it; the form rendered the error as readable text, not raw
   JSON: "We could not submit this report -- Equipment ID: Value error,
   equipment_id must contain only letters, digits and hyphens". See
   `02-invalid-equipment-id-readable-error.png`.

3. **Valid submission and lookup.** Submitted a real report (equipment
   LAB-01, D-Block d1, "Tower is not working", high, STU-2026-07) and
   received ticket `FR-EC7E64C3`. Looked it up again via the "Look up a
   ticket" form using only the ticket ID and got the same record back.
   See `03-valid-submission-and-lookup.png`.

4. **Second ticket, used for the status-update test.** Submitted
   another report (LAB-023, HP Lab hp 01, "Monitor is not working",
   high, STU-2026-008), got ticket `FR-E5B35F09`, and looked it up. See
   `04-second-ticket-lookup.png`.

5. **Status update through the UI form itself**, not curl/PATCH
   directly: entered `FR-E5B35F09`, selected "In progress", entered the
   maintenance key, clicked "Update status". The page showed "Status
   updated" with the ticket's status now `in_progress`. See
   `05-status-update-via-ui-form.png`.

6. **Confirmed in the database directly**, independent of the API
   response: `docker-compose exec db psql -U faultservice -d
   faultservice -c "SELECT ticket_id, equipment_id, status, priority
   FROM tickets;"` returned `FR-E5B35F09 | LAB-023 | in_progress | P1`,
   proving the UI's status change was really written to PostgreSQL, not
   just reflected back in the page. See
   `06-db-persistence-confirmed-psql.png`.

## Result

Pass. The dashboard's client-side validation, server-side validation
(rendered readably, not as raw JSON), normal submission/lookup, and the
maintenance status-update form all work end to end, with the status
change independently confirmed in the database.
