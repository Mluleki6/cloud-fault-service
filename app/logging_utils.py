"""
Structured logging helper.

Every accepted, rejected and failed event must produce a structured log
entry carrying the same correlation_id, so a marker (or a teammate) can
trace one event end-to-end -- this is Evidence E3 in the Milestone 3
evidence pack. In Cloud Run, anything written to stdout as JSON is
automatically picked up by Cloud Logging with no extra wiring.
"""
import json
import logging
import sys
from datetime import datetime, timezone

logger = logging.getLogger("fault_service")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)


def log_event(event: str, correlation_id: str, **fields) -> None:
    """Emit one structured JSON log line.

    event: short machine-readable event name, e.g.
           "fault_report.accepted", "fault_report.rejected",
           "fault_report.notify_failed", "fault_report.retrieved"
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "correlation_id": correlation_id,
        **fields,
    }
    logger.info(json.dumps(record))
