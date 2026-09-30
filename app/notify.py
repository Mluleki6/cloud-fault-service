"""
Downstream notification step.

Best-effort by design: a failure here must never fail the request or
block ticket creation (see app/main.py -- the caller catches
NotificationError and still returns 201). NOTIFY_FORCE_FAILURE=1 lets
the team deliberately trigger the dependency-failure test case required
in Milestone 3/4 without needing to actually take a real service down.

Real channel: set NOTIFY_WEBHOOK_URL to any webhook endpoint (n8n,
Discord, Slack, or a generic JSON receiver). If it is unset, this stays
a no-op success so the slice still runs with zero external accounts --
that was the original Milestone 1-3 behaviour and remains the default.
Set NOTIFY_WEBHOOK_FORMAT to "discord" or "slack" if the target expects
their specific payload shape instead of a generic JSON body.
"""
import os

import httpx

_TIMEOUT_SECONDS = 5.0


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


def notify_maintenance(ticket_id: str, equipment_id: str, priority: str) -> bool:
    if os.environ.get("NOTIFY_FORCE_FAILURE") == "1":
        raise NotificationError("Simulated notification service outage")

    webhook_url = os.environ.get("NOTIFY_WEBHOOK_URL")
    if not webhook_url:
        # No real channel configured -- keep the zero-dependency stub
        # behaviour so the slice still runs with no external account.
        return True

    fmt = os.environ.get("NOTIFY_WEBHOOK_FORMAT", "generic")
    payload = _build_payload(ticket_id, equipment_id, priority, fmt)
    try:
        response = httpx.post(webhook_url, json=payload, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise NotificationError(f"Webhook call failed: {exc}") from exc
    return True
