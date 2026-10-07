"""
Fault Reporting Service -- FastAPI app.

Endpoints:
  GET   /                      simple HTML form for submitting and looking up tickets
  POST  /faults                submit a fault report (use cases 1-6, 8)
  GET   /faults/{id}           retrieve a ticket by ID (use case 7)
  PATCH /faults/{id}/status    maintenance-only: move a ticket to a new status
  GET   /health                liveness check

Run locally:      uvicorn app.main:app --reload
Run in Docker:    see docker-compose.yml
Deploy to Cloud Run:  see scripts/deploy_gcp.sh
"""
import hmac
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.logging_utils import log_event
from app.notify import notify_maintenance, NotificationError
from app.persistence import (
    Base,
    SessionLocal,
    Ticket,
    engine,
    get_ticket,
    init_db,
    save_ticket,
    update_ticket_status,
)
from app.processing import derive_priority, generate_ticket_id, now_utc
from app.schemas import ErrorResponse, FaultReportIn, FaultReportOut, StatusUpdateIn


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Fault Reporting Service", version="0.1.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def malformed_request_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Catches body-validation failures that happen before the handler's
    # own try/except runs: not valid JSON, valid JSON that isn't an
    # object, or (since the status-update endpoint was added) a
    # well-formed body with a field value FastAPI's own typed
    # parameter rejects, e.g. an invalid status enum on PATCH
    # .../status. Without this, FastAPI's default handler returns a
    # differently-shaped error with no correlation_id, breaking the
    # same error contract documented in architecture/event-contract.json
    # and skipping the structured log Q4 requires for every rejected
    # event.
    #
    # The detail message used to unconditionally say "is not valid
    # JSON", which was only ever true for the first case. Found by
    # Andiswa Xulu testing an invalid status value: the JSON was
    # perfectly well-formed, the real problem was an enum mismatch, but
    # the top-level detail claimed a JSON parsing failure while the
    # errors array correctly named the real one. Distinguish the two
    # instead of guessing.
    correlation_id = str(uuid.uuid4())
    safe_errors = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    is_json_parse_failure = any(e.get("type") == "json_invalid" for e in safe_errors)
    detail = (
        "The request body is missing or is not valid JSON."
        if is_json_parse_failure
        else "One or more fields failed validation."
    )
    log_event(
        "fault_report.rejected",
        correlation_id,
        reason="malformed_request",
        errors=safe_errors,
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "detail": detail,
            "correlation_id": correlation_id,
            "errors": safe_errors,
        },
    )


_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def serve_form():
    # A plain HTML form so a reporter can use this without reading API
    # docs. Calls the same POST /faults and GET /faults/{id} endpoints
    # below, no separate backend path, no authentication, no new scope.
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/ticket", include_in_schema=False)
def serve_ticket_page():
    # A separate maintenance-facing page, distinct from the reporter's
    # form above: ticket lookup plus the status-update control. The
    # notification email links here (see app/notify.py, _ticket_url()),
    # so opening a ticket from an email lands on a focused dashboard
    # instead of the reporter's submission form.
    return FileResponse(_STATIC_DIR / "ticket.html")


def _to_out(ticket: Ticket, correlation_id: str) -> FaultReportOut:
    return FaultReportOut(
        ticket_id=ticket.ticket_id,
        correlation_id=correlation_id,
        equipment_id=ticket.equipment_id,
        location=ticket.location,
        description=ticket.description,
        severity=ticket.severity,
        priority=ticket.priority,
        status=ticket.status,
        reporter_id=ticket.reporter_id,
        created_at=ticket.created_at,
        notified=ticket.notified,
    )


def _raise_db_unavailable(correlation_id: str, ticket_id: Optional[str] = None) -> None:
    # Covers a *real* database outage (connection refused, server
    # closed the connection, etc.), not just the DB_FORCE_FAILURE
    # simulation flag below. Without this, a genuine outage was
    # bubbling up as an unhandled sqlalchemy.exc.OperationalError and
    # a raw 500, which is exactly the "crash" Q3 says the system must
    # not do -- found by actually stopping the db container and
    # watching it happen, not assumed safe from the simulated test.
    log_event("fault_report.db_unavailable", correlation_id, ticket_id=ticket_id)
    raise HTTPException(
        status_code=503,
        detail={
            "error": "dependency_unavailable",
            "detail": "The datastore is currently unavailable. Please retry shortly.",
            "correlation_id": correlation_id,
        },
    )


def _maintenance_key_valid(provided: Optional[str]) -> bool:
    configured = os.environ.get("MAINTENANCE_API_KEY")
    if not configured or not provided:
        return False
    return hmac.compare_digest(provided, configured)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/faults", response_model=FaultReportOut, status_code=201)
def submit_fault_report(payload: dict):
    correlation_id = str(uuid.uuid4())

    # --- Validation -----------------------------------------------------
    try:
        report = FaultReportIn(**payload)
    except ValidationError as exc:
        # Pydantic v2 error dicts can contain non-JSON-serialisable values
        # (e.g. exception objects in "ctx"), so only pass through the
        # plain, serialisable fields into the HTTP response and the log.
        safe_errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        log_event(
            "fault_report.rejected",
            correlation_id,
            reason="validation_error",
            errors=safe_errors,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "detail": "One or more fields failed validation.",
                "correlation_id": correlation_id,
                "errors": safe_errors,
            },
        )

    log_event("fault_report.accepted", correlation_id, equipment_id=report.equipment_id)

    # --- Processing -------------------------------------------------------
    ticket_id = generate_ticket_id()
    priority = derive_priority(report.severity)
    created_at = now_utc()

    # --- Persistence (dependency-failure case lives here) -----------------
    if os.environ.get("DB_FORCE_FAILURE") == "1":
        _raise_db_unavailable(correlation_id, ticket_id=ticket_id)

    session = SessionLocal()
    try:
        ticket = Ticket(
            ticket_id=ticket_id,
            correlation_id=correlation_id,
            equipment_id=report.equipment_id,
            location=report.location,
            description=report.description,
            severity=report.severity.value,
            priority=priority,
            status="open",
            reporter_id=report.reporter_id,
            created_at=created_at,
            notified=False,
        )
        try:
            ticket = save_ticket(session, ticket)
        except SQLAlchemyError:
            session.rollback()
            _raise_db_unavailable(correlation_id, ticket_id=ticket_id)

        # --- Notification (recovery/degradation case lives here) ----------
        try:
            notified = notify_maintenance(
                ticket_id,
                report.equipment_id,
                priority,
                location=report.location,
                description=report.description,
                severity=report.severity.value,
                reporter_id=report.reporter_id,
            )
            ticket.notified = notified
            session.commit()
            log_event("fault_report.notified", correlation_id, ticket_id=ticket_id)
        except NotificationError as exc:
            # Degrade gracefully: the ticket is still valid and persisted,
            # notification failure does not corrupt state or fail the
            # request -- it's logged so it can be retried/escalated.
            log_event(
                "fault_report.notify_failed",
                correlation_id,
                ticket_id=ticket_id,
                reason=str(exc),
            )

        log_event(
            "fault_report.persisted",
            correlation_id,
            ticket_id=ticket_id,
            priority=priority,
        )
        return _to_out(ticket, correlation_id)
    finally:
        session.close()


@app.get("/faults/{ticket_id}", response_model=FaultReportOut)
def retrieve_fault_report(ticket_id: str):
    correlation_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        try:
            ticket = get_ticket(session, ticket_id)
        except SQLAlchemyError:
            _raise_db_unavailable(correlation_id, ticket_id=ticket_id)
        if ticket is None:
            log_event("fault_report.not_found", correlation_id, ticket_id=ticket_id)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": f"No ticket found for id {ticket_id}",
                    "correlation_id": correlation_id,
                },
            )
        log_event("fault_report.retrieved", correlation_id, ticket_id=ticket_id)
        return _to_out(ticket, ticket.correlation_id)
    finally:
        session.close()


@app.patch("/faults/{ticket_id}/status", response_model=FaultReportOut)
def update_fault_status(
    ticket_id: str,
    payload: StatusUpdateIn,
    x_maintenance_key: Optional[str] = Header(default=None),
):
    # Maintenance-only: moves a ticket between open, in_progress and
    # resolved. Gated by a single shared secret (MAINTENANCE_API_KEY)
    # rather than per-user accounts -- deliberately the smallest
    # mechanism that still tells "the maintenance team" apart from a
    # reporter, not a login system. If the key is not configured at
    # all, every request is refused rather than silently left open.
    correlation_id = str(uuid.uuid4())

    if not _maintenance_key_valid(x_maintenance_key):
        log_event("fault_report.status_update_forbidden", correlation_id, ticket_id=ticket_id)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "detail": "A valid maintenance key is required to update ticket status.",
                "correlation_id": correlation_id,
            },
        )

    session = SessionLocal()
    try:
        try:
            ticket = get_ticket(session, ticket_id)
        except SQLAlchemyError:
            _raise_db_unavailable(correlation_id, ticket_id=ticket_id)
        if ticket is None:
            log_event("fault_report.not_found", correlation_id, ticket_id=ticket_id)
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "detail": f"No ticket found for id {ticket_id}",
                    "correlation_id": correlation_id,
                },
            )
        old_status = ticket.status
        try:
            ticket = update_ticket_status(session, ticket, payload.status.value)
        except SQLAlchemyError:
            session.rollback()
            _raise_db_unavailable(correlation_id, ticket_id=ticket_id)
        log_event(
            "fault_report.status_updated",
            correlation_id,
            ticket_id=ticket_id,
            old_status=old_status,
            new_status=ticket.status,
        )
        return _to_out(ticket, correlation_id)
    finally:
        session.close()
