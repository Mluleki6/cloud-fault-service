"""
Unit tests for the real webhook notification path (app/notify.py).

These are separate from the API-level notification tests in
test_api.py, which cover the "no channel configured" default (stub,
always succeeds) and the forced-failure degradation path. This file
covers the new NOTIFY_WEBHOOK_URL behaviour on its own, with the HTTP
call mocked so no test ever makes a real network request.
"""
import httpx
import pytest

from app.notify import NotificationError, notify_maintenance


def test_no_channel_configured_stays_a_noop(monkeypatch):
    monkeypatch.delenv("NOTIFY_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("NOTIFY_EMAIL_API_KEY", raising=False)
    assert notify_maintenance("FR-1", "LAB-014", "P1") is True


def test_email_success_sends_via_resend(monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL_API_KEY", "re_test_key")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "maintenance@example.test")
    monkeypatch.delenv("NOTIFY_WEBHOOK_URL", raising=False)

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    assert notify_maintenance("FR-5", "LAB-014", "P1") is True
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test_key"
    assert captured["json"]["from"] == "onboarding@resend.dev"
    assert captured["json"]["to"] == ["maintenance@example.test"]
    assert "FR-5" in captured["json"]["subject"]
    assert "LAB-014" in captured["json"]["text"]


def test_email_takes_priority_over_webhook(monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL_API_KEY", "re_test_key")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "maintenance@example.test")
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")

    called_urls = []

    def fake_post(url, timeout, **kwargs):
        called_urls.append(url)
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    notify_maintenance("FR-6", "LAB-014", "P1")
    assert called_urls == ["https://api.resend.com/emails"]


def test_email_missing_recipient_raises_notification_error(monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL_API_KEY", "re_test_key")
    monkeypatch.delenv("NOTIFY_EMAIL_TO", raising=False)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-7", "LAB-014", "P1")


def test_email_http_error_raises_notification_error(monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL_API_KEY", "re_test_key")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "maintenance@example.test")

    def fake_post(url, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(401, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-8", "LAB-014", "P1")


def test_webhook_success_posts_generic_payload(monkeypatch):
    monkeypatch.delenv("NOTIFY_EMAIL_API_KEY", raising=False)
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")
    monkeypatch.delenv("NOTIFY_WEBHOOK_FORMAT", raising=False)

    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    assert notify_maintenance(
        "FR-1", "LAB-014", "P1",
        location="Room 214", description="Projector down.",
        severity="high", reporter_id="STU-001",
    ) is True
    assert captured["url"] == "https://example.test/webhook"
    assert captured["json"] == {
        "ticket_id": "FR-1",
        "equipment_id": "LAB-014",
        "priority": "P1",
        "location": "Room 214",
        "description": "Projector down.",
        "severity": "high",
        "reporter_id": "STU-001",
        "ticket_url": "http://localhost:8080/?ticket_id=FR-1",
        "message": (
            "New fault ticket FR-1 (LAB-014) - priority P1\n"
            "Reported by: STU-001 at Room 214\n"
            "Severity: high\n"
            "Description: Projector down.\n"
            "View and update this ticket: http://localhost:8080/?ticket_id=FR-1"
        ),
    }


def test_webhook_discord_format_wraps_content(monkeypatch):
    monkeypatch.delenv("NOTIFY_EMAIL_API_KEY", raising=False)
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/discord")
    monkeypatch.setenv("NOTIFY_WEBHOOK_FORMAT", "discord")

    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return httpx.Response(204, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    notify_maintenance(
        "FR-2", "AC-203", "P3",
        location="Room 2", description="Noisy aircon.",
        severity="low", reporter_id="STU-002",
    )
    assert captured["json"] == {"content": (
        "New fault ticket FR-2 (AC-203) - priority P3\n"
        "Reported by: STU-002 at Room 2\n"
        "Severity: low\n"
        "Description: Noisy aircon.\n"
        "View and update this ticket: http://localhost:8080/?ticket_id=FR-2"
    )}


def test_webhook_http_error_raises_notification_error(monkeypatch):
    monkeypatch.delenv("NOTIFY_EMAIL_API_KEY", raising=False)
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")

    def fake_post(url, json, timeout):
        raise httpx.ConnectTimeout("connection timed out")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-3", "LAB-014", "P2")


def test_webhook_non_2xx_status_raises_notification_error(monkeypatch):
    monkeypatch.delenv("NOTIFY_EMAIL_API_KEY", raising=False)
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")

    def fake_post(url, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(500, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-4", "LAB-014", "P1")


def test_email_connection_timeout_raises_notification_error(monkeypatch):
    # Mirrors test_webhook_http_error_raises_notification_error above,
    # but for the email path: a connection timeout is a different kind
    # of failure than an HTTP error status (e.g. the 401 covered by
    # test_email_http_error_raises_notification_error) and wasn't
    # covered until now.
    monkeypatch.setenv("NOTIFY_EMAIL_API_KEY", "re_test_key")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "maintenance@example.test")

    def fake_post(url, headers, json, timeout):
        raise httpx.ConnectTimeout("connection timed out")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-9", "LAB-014", "P1")
