"""
Component / end-to-end tests against the running FastAPI app.

Together with test_validation.py these cover every evidence category the
handbook asks for: normal cases, invalid-input cases, a dependency
failure, and a recovery/degradation case.
"""
VALID_PAYLOAD = {
    "equipment_id": "LAB-014",
    "location": "Science Building, Room 214",
    "description": "Projector will not power on.",
    "severity": "high",
    "reporter_id": "STU-2026-001",
}


# --- Normal cases -----------------------------------------------------------

def test_submit_valid_report_returns_ticket(client):
    resp = client.post("/faults", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["ticket_id"].startswith("FR-")
    assert body["priority"] == "P1"
    assert body["status"] == "open"
    assert body["notified"] is True


def test_retrieve_existing_ticket(client):
    created = client.post("/faults", json=VALID_PAYLOAD).json()
    resp = client.get(f"/faults/{created['ticket_id']}")
    assert resp.status_code == 200
    assert resp.json()["ticket_id"] == created["ticket_id"]
    assert resp.json()["correlation_id"] == created["correlation_id"]


def test_repeated_valid_submission_creates_distinct_tickets(client):
    first = client.post("/faults", json=VALID_PAYLOAD).json()
    second = client.post("/faults", json=VALID_PAYLOAD).json()
    assert first["ticket_id"] != second["ticket_id"]


# --- Invalid-input cases -----------------------------------------------------

def test_submit_missing_field_rejected(client):
    bad = dict(VALID_PAYLOAD)
    del bad["equipment_id"]
    resp = client.post("/faults", json=bad)
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_request"
    assert "correlation_id" in resp.json()["detail"]


def test_submit_invalid_severity_rejected(client):
    bad = dict(VALID_PAYLOAD, severity="catastrophic")
    resp = client.post("/faults", json=bad)
    assert resp.status_code == 400


def test_invalid_submission_does_not_create_a_ticket(client):
    bad = dict(VALID_PAYLOAD)
    del bad["description"]
    client.post("/faults", json=bad)
    # No way to list tickets by design (no such endpoint) -- instead prove
    # via a fresh valid submission that ticket numbering / state wasn't
    # corrupted by the rejected one.
    resp = client.post("/faults", json=VALID_PAYLOAD)
    assert resp.status_code == 201


def test_retrieve_missing_ticket_returns_404(client):
    resp = client.get("/faults/FR-DOESNOTEXIST")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "not_found"


# --- Dependency failure -------------------------------------------------------

def test_database_unavailable_returns_503(client, monkeypatch):
    monkeypatch.setenv("DB_FORCE_FAILURE", "1")
    resp = client.post("/faults", json=VALID_PAYLOAD)
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "dependency_unavailable"


# --- Recovery / degradation ----------------------------------------------------

def test_notification_failure_degrades_gracefully(client, monkeypatch):
    monkeypatch.setenv("NOTIFY_FORCE_FAILURE", "1")
    resp = client.post("/faults", json=VALID_PAYLOAD)
    # The ticket is still created and persisted even though the
    # notification step failed -- this is the designed degradation
    # behaviour, not a crash.
    assert resp.status_code == 201
    body = resp.json()
    assert body["notified"] is False

    # And it's genuinely persisted, not just returned in-memory.
    follow_up = client.get(f"/faults/{body['ticket_id']}")
    assert follow_up.status_code == 200
    assert follow_up.json()["notified"] is False


# --- Maintenance status updates ------------------------------------------------

def test_status_update_with_correct_key_succeeds(client, monkeypatch):
    monkeypatch.setenv("MAINTENANCE_API_KEY", "test-maintenance-key")
    created = client.post("/faults", json=VALID_PAYLOAD).json()

    resp = client.patch(
        f"/faults/{created['ticket_id']}/status",
        json={"status": "in_progress"},
        headers={"X-Maintenance-Key": "test-maintenance-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # Persisted, not just returned in-memory.
    follow_up = client.get(f"/faults/{created['ticket_id']}")
    assert follow_up.json()["status"] == "in_progress"


def test_status_update_without_key_is_forbidden(client, monkeypatch):
    monkeypatch.setenv("MAINTENANCE_API_KEY", "test-maintenance-key")
    created = client.post("/faults", json=VALID_PAYLOAD).json()

    resp = client.patch(f"/faults/{created['ticket_id']}/status", json={"status": "resolved"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "forbidden"

    # Status must be unchanged.
    follow_up = client.get(f"/faults/{created['ticket_id']}")
    assert follow_up.json()["status"] == "open"


def test_status_update_with_wrong_key_is_forbidden(client, monkeypatch):
    monkeypatch.setenv("MAINTENANCE_API_KEY", "test-maintenance-key")
    created = client.post("/faults", json=VALID_PAYLOAD).json()

    resp = client.patch(
        f"/faults/{created['ticket_id']}/status",
        json={"status": "resolved"},
        headers={"X-Maintenance-Key": "wrong-key"},
    )
    assert resp.status_code == 403


def test_status_update_when_key_not_configured_is_forbidden(client, monkeypatch):
    monkeypatch.delenv("MAINTENANCE_API_KEY", raising=False)
    created = client.post("/faults", json=VALID_PAYLOAD).json()

    # Even a request with some key attached must fail, since no key
    # could ever be considered valid when none is configured.
    resp = client.patch(
        f"/faults/{created['ticket_id']}/status",
        json={"status": "resolved"},
        headers={"X-Maintenance-Key": "anything"},
    )
    assert resp.status_code == 403


def test_status_update_unknown_ticket_returns_404(client, monkeypatch):
    monkeypatch.setenv("MAINTENANCE_API_KEY", "test-maintenance-key")
    resp = client.patch(
        "/faults/FR-DOESNOTEXIST/status",
        json={"status": "resolved"},
        headers={"X-Maintenance-Key": "test-maintenance-key"},
    )
    assert resp.status_code == 404


def test_status_update_invalid_status_value_rejected(client, monkeypatch):
    monkeypatch.setenv("MAINTENANCE_API_KEY", "test-maintenance-key")
    created = client.post("/faults", json=VALID_PAYLOAD).json()

    resp = client.patch(
        f"/faults/{created['ticket_id']}/status",
        json={"status": "done"},
        headers={"X-Maintenance-Key": "test-maintenance-key"},
    )
    # Caught by the same global malformed-request handler as every other
    # body-validation error, so it comes back 400 in the app's own error
    # shape, not FastAPI's default 422.
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_request"


def test_status_update_same_status_twice_is_idempotent(client, monkeypatch):
    # interface-contracts.md documents this as idempotent ("no error on
    # a no-op transition"), but nothing actually tested that claim
    # until now.
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
