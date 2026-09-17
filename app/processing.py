"""
The one "useful processing rule" the handbook requires -- not an echo of
the input. Turns a validated report into a ticket with a generated ID
and a derived priority.
"""
import uuid
from datetime import datetime, timezone

from app.schemas import Severity

# Severity -> priority mapping is intentionally a real business rule:
# high severity always becomes P1 regardless of anything else, medium
# becomes P2, low becomes P3. A more advanced version could also weigh
# equipment category or location, but this is enough to be "useful"
# rather than decorative.
_PRIORITY_MAP = {
    Severity.high: "P1",
    Severity.medium: "P2",
    Severity.low: "P3",
}


def generate_ticket_id() -> str:
    return f"FR-{uuid.uuid4().hex[:8].upper()}"


def derive_priority(severity: Severity) -> str:
    return _PRIORITY_MAP[severity]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
