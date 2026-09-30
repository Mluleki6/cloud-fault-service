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


def test_no_webhook_configured_stays_a_noop(monkeypatch):
    monkeypatch.delenv("NOTIFY_WEBHOOK_URL", raising=False)
    assert notify_maintenance("FR-1", "LAB-014", "P1") is True


def test_webhook_success_posts_generic_payload(monkeypatch):
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")
    monkeypatch.delenv("NOTIFY_WEBHOOK_FORMAT", raising=False)

    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    assert notify_maintenance("FR-1", "LAB-014", "P1") is True
    assert captured["url"] == "https://example.test/webhook"
    assert captured["json"] == {
        "ticket_id": "FR-1",
        "equipment_id": "LAB-014",
        "priority": "P1",
        "message": "New fault ticket FR-1 (LAB-014) - priority P1",
    }


def test_webhook_discord_format_wraps_content(monkeypatch):
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/discord")
    monkeypatch.setenv("NOTIFY_WEBHOOK_FORMAT", "discord")

    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return httpx.Response(204, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    notify_maintenance("FR-2", "AC-203", "P3")
    assert captured["json"] == {"content": "New fault ticket FR-2 (AC-203) - priority P3"}


def test_webhook_http_error_raises_notification_error(monkeypatch):
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")

    def fake_post(url, json, timeout):
        raise httpx.ConnectTimeout("connection timed out")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-3", "LAB-014", "P2")


def test_webhook_non_2xx_status_raises_notification_error(monkeypatch):
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://example.test/webhook")

    def fake_post(url, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(500, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(NotificationError):
        notify_maintenance("FR-4", "LAB-014", "P1")
