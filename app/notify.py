"""
Downstream notification step.

Best-effort by design: a failure here must never fail the request or
block ticket creation (see app/main.py -- the caller catches
NotificationError and still returns 201). NOTIFY_FORCE_FAILURE=1 lets
the team deliberately trigger the dependency-failure test case required
in Milestone 3/4 without needing to actually take a real service down.

Two real channels are supported, checked in this order:

1. Direct email via the Resend API, if NOTIFY_EMAIL_API_KEY is set.
   This is the channel that actually puts a message in the maintenance
   contact's inbox, which is what the proposal describes.
2. A generic webhook (n8n, Discord, Slack, or any JSON receiver), if
   NOTIFY_WEBHOOK_URL is set instead.

If neither is set, this stays a no-op success so the slice still runs
with zero external accounts -- that was the original Milestone 1-3
behaviour and remains the default.
"""
import os

import httpx

_TIMEOUT_SECONDS = 5.0
_RESEND_API_URL = "https://api.resend.com/emails"


class NotificationError(Exception):
    pass


def _build_payload(ticket_id: str, equipment_id: str, priority: str, fmt: str) -> dict:
    message = f"New fault ticket {ticket_id} ({equipment_id}) - priority {priority}"
    if fmt == "discord":
        return {"content": message}
    if fmt == "slack":
        return {"text": message}
    return {
        "ticket_id": ticket_id,
        "equipment_id": equipment_id,
        "priority": priority,
        "message": message,
    }


def _send_email(ticket_id: str, equipment_id: str, priority: str) -> None:
    api_key = os.environ["NOTIFY_EMAIL_API_KEY"]
    to_address = os.environ.get("NOTIFY_EMAIL_TO")
    if not to_address:
        raise NotificationError("NOTIFY_EMAIL_API_KEY is set but NOTIFY_EMAIL_TO is missing")
    from_address = os.environ.get("NOTIFY_EMAIL_FROM", "onboarding@resend.dev")

    subject = f"New fault ticket {ticket_id} (priority {priority})"
    body = (
        f"A new fault report has been logged.\n\n"
        f"Ticket ID: {ticket_id}\n"
        f"Equipment: {equipment_id}\n"
        f"Priority: {priority}\n\n"
        f"Look this ticket up at the Fault Reporting Service to see full details."
    )
    try:
        response = httpx.post(
            _RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": from_address, "to": [to_address], "subject": subject, "text": body},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise NotificationError(f"Email send failed: {exc}") from exc


def _send_webhook(ticket_id: str, equipment_id: str, priority: str) -> None:
    webhook_url = os.environ["NOTIFY_WEBHOOK_URL"]
    fmt = os.environ.get("NOTIFY_WEBHOOK_FORMAT", "generic")
    payload = _build_payload(ticket_id, equipment_id, priority, fmt)
    try:
        response = httpx.post(webhook_url, json=payload, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise NotificationError(f"Webhook call failed: {exc}") from exc


def notify_maintenance(ticket_id: str, equipment_id: str, priority: str) -> bool:
    if os.environ.get("NOTIFY_FORCE_FAILURE") == "1":
        raise NotificationError("Simulated notification service outage")

    if os.environ.get("NOTIFY_EMAIL_API_KEY"):
        _send_email(ticket_id, equipment_id, priority)
        return True

    if os.environ.get("NOTIFY_WEBHOOK_URL"):
        _send_webhook(ticket_id, equipment_id, priority)
        return True

    # No real channel configured -- keep the zero-dependency stub
    # behaviour so the slice still runs with no external account.
    return True
