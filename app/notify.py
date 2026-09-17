"""
Downstream notification step.

Kept as a thin, swappable function on purpose: for the real deployment
this can call a Resend/SendGrid API or hit an n8n webhook (the same
pattern used in the UniZulu Asset Management project) to email the
maintenance contact. For the vertical slice it simulates that call so
the whole system runs without any external account.

NOTIFY_FORCE_FAILURE=1 lets the team deliberately trigger the
dependency-failure test case required in Milestone 3/4 without needing
to actually take a real service down.
"""
import os


class NotificationError(Exception):
    pass


def notify_maintenance(ticket_id: str, equipment_id: str, priority: str) -> bool:
    if os.environ.get("NOTIFY_FORCE_FAILURE") == "1":
        raise NotificationError("Simulated notification service outage")

    # Real implementation would POST to an n8n webhook or an email API here.
    # Left as a no-op success so the slice is runnable with zero external
    # dependencies; swap this out once a real notification channel is wired up.
    return True
