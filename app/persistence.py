"""
Persistence layer.

Local/dev/CI: DATABASE_URL defaults to a SQLite file so the test suite
and `docker compose up` both work with zero external setup.
Cloud mapping: DATABASE_URL is swapped for a Cloud SQL (Postgres)
connection string when deployed to Cloud Run -- same code, same
SQLAlchemy models, only the connection string changes. That equivalence
is exactly what the report's "local option -> managed cloud service"
mapping table needs to show.
"""
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./fault_service.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String, primary_key=True)
    correlation_id = Column(String, nullable=False)
    equipment_id = Column(String, nullable=False)
    location = Column(String, nullable=False)
    description = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    reporter_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    notified = Column(Boolean, nullable=False, default=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def save_ticket(session, ticket: Ticket) -> Ticket:
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


def get_ticket(session, ticket_id: str):
    return session.get(Ticket, ticket_id)
