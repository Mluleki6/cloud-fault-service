# Team tasks

Everyone now has push access to this repository. This file is
self-contained: find your name below and follow your steps, you do not
need to wait for or ask anyone else. If this is your first time using
git, every command you need is written out exactly below, copy them as
they are.

## Everyone: get the project onto your computer (do this once)

1. Install Docker Desktop if you haven't:
   https://www.docker.com/products/docker-desktop/
2. Install Git if you don't have it: https://git-scm.com/downloads
3. Open a terminal (Windows: search "cmd" or "PowerShell"; Mac: "Terminal")
   and run:

   ```
   git clone https://github.com/Mluleki6/cloud-fault-service.git
   cd cloud-fault-service
   ```

   If GitHub asks you to sign in, use the account you were invited
   with.

4. Start the project:

   ```
   docker compose up --build
   ```

   Wait for it to settle (a minute or two the first time), then open
   http://localhost:8080/ in your browser.

5. Before you make any change below, always run this first so you have
   the latest version:

   ```
   git pull
   ```

---

## Andiswa Ngcobo (Andiswa23) — update the architecture diagram

The diagram in `architecture/architecture-diagram.md` was drawn before
the maintenance status-update feature (`PATCH /faults/{id}/status`)
existed. It needs one more path added: maintenance team, using a
shared key, moving a ticket through open, in progress, resolved.

1. Open `architecture/architecture-diagram.md` in a text editor.
2. Read the existing Mermaid diagram (the ```mermaid code block) and
   the annotation tables below it, to see the style already used.
3. Add the new path: a box or note for the maintenance team, an arrow
   from it to the API endpoint for the status-update call, matching
   the existing visual style (see how Notification or Persistence are
   drawn for reference).
4. Save, then in your terminal:

   ```
   git add architecture/architecture-diagram.md
   git commit -m "Add maintenance status-update path to the event-flow diagram"
   git push
   ```

5. Tell the team when it's pushed. Check `git log --oneline -5`
   afterward, your commit should be at the top.

---

## Mzameni Nkosi (mzamonkosi50-coder) — prove real email works

This is the one thing nobody has verified with a real account yet:
does a fault report actually produce an email someone receives.

1. Go to https://resend.com, sign up free (no card needed).
2. Create an API key in their dashboard, copy it (starts with "re_").
3. In your local `cloud-fault-service` folder, copy `.env.example` to
   a new file named exactly `.env` (this file is already in
   `.gitignore`, it will never be committed, that's intentional, it's
   your personal key).
4. Open `.env`, fill in:

   ```
   NOTIFY_EMAIL_API_KEY=re_your_real_key
   NOTIFY_EMAIL_TO=your_own_email_address
   ```

5. Restart: `docker compose up --build`
6. Submit a report at http://localhost:8080/, check your inbox.
7. Take a screenshot of the email and the ticket response.
8. Write up what happened. Create a new file
   `evidence/milestone4_email_verification_mzameni.md` with: what you
   did, whether the email arrived, how long it took, anything that was
   confusing. Describe the screenshot content in words (don't paste
   real email addresses or API keys into this file).

9. Now build something: there's a real gap in the automated tests.
   `tests/test_notify.py` tests what happens when the email provider
   returns an error (like a 401), but not what happens if the
   connection just times out, a different kind of failure. Open
   `tests/test_notify.py`, find the test called
   `test_webhook_http_error_raises_notification_error` near the bottom
   (it tests this exact scenario for the webhook path using
   `httpx.ConnectTimeout`), and add this new test anywhere in the file,
   matching the existing style:

   ```python
   def test_email_connection_timeout_raises_notification_error(monkeypatch):
       monkeypatch.setenv("NOTIFY_EMAIL_API_KEY", "re_test_key")
       monkeypatch.setenv("NOTIFY_EMAIL_TO", "maintenance@example.test")

       def fake_post(url, headers, json, timeout):
           raise httpx.ConnectTimeout("connection timed out")

       monkeypatch.setattr(httpx, "post", fake_post)

       with pytest.raises(NotificationError):
           notify_maintenance("FR-9", "LAB-014", "P1")
   ```

   Run `pytest tests/test_notify.py -v` and confirm it passes along
   with all the others (should say something like "10 passed").

10. Commit both files together:

    ```
    git add evidence/milestone4_email_verification_mzameni.md tests/test_notify.py
    git commit -m "Verify real email notification; add missing connection-timeout test"
    git push
    ```

---

## Sandile Luthuli (SANDILE027) — prove status updates work

1. In your local `cloud-fault-service` folder, copy `.env.example` to
   `.env` (not committed, this is yours).
2. Make up your own key, any text at least 10 characters, and put it
   in `.env`:

   ```
   MAINTENANCE_API_KEY=whatever-you-make-up-here
   ```

3. Restart: `docker compose up --build`
4. At http://localhost:8080/, submit a report, copy its ticket ID.
5. Scroll to "Maintenance team: update a ticket's status". Enter the
   ticket ID, pick "In progress", enter the same key you made up,
   click Update status. It should succeed.
6. Try again with the wrong key on purpose. It should be refused.
7. Screenshot both results.
8. Create `evidence/milestone4_status_update_verification_sandile.md`
   describing what you did and what happened (don't include your real
   key value in this file).

9. Now build something: the docs claim that setting a ticket to the
   same status twice is harmless (no error), but nothing actually
   tests this. Open `tests/test_api.py`, scroll to the bottom where
   the other status-update tests are (functions starting with
   `test_status_update_`), and add this new one below them, matching
   the existing style:

   ```python
   def test_status_update_same_status_twice_is_idempotent(client, monkeypatch):
       monkeypatch.setenv("MAINTENANCE_API_KEY", "test-maintenance-key")
       created = client.post("/faults", json=VALID_PAYLOAD).json()

       first = client.patch(
           f"/faults/{created['ticket_id']}/status",
           json={"status": "in_progress"},
           headers={"X-Maintenance-Key": "test-maintenance-key"},
       )
       second = client.patch(
           f"/faults/{created['ticket_id']}/status",
           json={"status": "in_progress"},
           headers={"X-Maintenance-Key": "test-maintenance-key"},
       )

       assert first.status_code == 200
       assert second.status_code == 200
       assert second.json()["status"] == "in_progress"
   ```

   Run `pytest tests/test_api.py -v` and confirm it passes along with
   all the others (should say something like "16 passed").

10. Commit both files together:

    ```
    git add evidence/milestone4_status_update_verification_sandile.md tests/test_api.py
    git commit -m "Verify maintenance status update; add missing idempotency test"
    git push
    ```

---

## Andiswa Anele Xulu (Jiba14) — teardown and rebuild check, plus a proofread

1. With the project running, tear it down completely:

   ```
   docker compose down -v
   ```

   Confirm with `docker compose ps` that nothing is listed.

2. Bring it back up from nothing:

   ```
   docker compose up --build
   ```

3. Submit a report at http://localhost:8080/ to confirm it's genuinely
   working again after a full teardown, not just that the containers
   started.
4. Read `architecture/decisions/0002-maintenance-status-updates.md`
   (the record of why the status-update feature was added). Note
   anything unclear or that you'd word differently.

5. Now build something: a proper Test Record, using the exact template
   from the handbook (section 9.2), for the teardown/rebuild check you
   just did. Create a new file `evidence/test_record_andiswax.md` with
   this table filled in with your own real results (not copied from
   anywhere, your own run):

   ```markdown
   # Test Record — Teardown and Rebuild Check

   | Field | Entry |
   |---|---|
   | Test ID and requirement | TR-01, handbook section 7.1 teardown/rebuild check |
   | Input/precondition | Project running via docker compose up |
   | Expected result | docker compose down -v removes everything; docker compose up --build recreates a working service from nothing |
   | Actual result | (fill in what actually happened for you) |
   | Correlation/evidence reference | (paste a ticket_id or correlation_id from a report you submitted after rebuilding) |
   | Pass/fail and defect link | (pass or fail, and if fail, describe what went wrong) |
   | Retest result | (only fill in if you had to retry) |
   ```

6. Commit everything together:

   ```
   git add evidence/milestone4_teardown_verification_andiswax.md evidence/test_record_andiswax.md
   git commit -m "Verify teardown and rebuild, proofread status-update ADR, add formal test record"
   git push
   ```

---

## When everyone's done

Run `git log --oneline -10` in the project folder, you should see five
different names (or usernames) across recent commits, not just one.
That's the actual evidence the handbook's team-contribution criterion
is asking for.
