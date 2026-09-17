"""
Fault Reporting Service -- FastAPI app.

Endpoints:
  POST /faults        submit a fault report (use cases 1-6, 8)
  GET  /faults/{id}    retrieve a ticket by ID (use case 7)
  GET  /health         liveness check

Run locally:      uvicorn app.main:app --reload
Run in Docker:    see docker-compose.yml
Deploy to Cloud Run:  see scripts/deploy_gcp.sh
"""
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.logging_utils import log_event
from app.notify import notify_maintenance, NotificationError
from app.persistence import Base, SessionLocal, Ticket, engine, get_ticket, init_db, save_ticket
from app.processing import derive_priority, generate_ticket_id, now_utc
from app.schemas import ErrorResponse, FaultReportIn, FaultReportOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Fault Reporting Service", version="0.1.0", lifespan=lifespan)


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
        log_event("fault_report.db_unavailable", correlation_id, ticket_id=ticket_id)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "dependency_unavailable",
                "detail": "The datastore is currently unavailable. Please retry shortly.",
                "correlation_id": correlation_id,
            },
        )

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
        ticket = save_ticket(session, ticket)

        # --- Notification (recovery/degradation case lives here) ----------
        try:
            notified = notify_maintenance(ticket_id, report.equipment_id, priority)
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
    finally:
        session.close()


@app.get("/faults/{ticket_id}", response_model=FaultReportOut)
def retrieve_fault_report(ticket_id: str):
    correlation_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        ticket = get_ticket(session, ticket_id)
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
        return FaultReportOut(
            ticket_id=ticket.ticket_id,
            correlation_id=ticket.correlation_id,
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
    finally:
        session.close()
