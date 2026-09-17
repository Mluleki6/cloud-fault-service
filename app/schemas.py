"""
Pydantic request/response models for the Fault Reporting Service.

These models are the first line of validation (type, required/optional,
allowed values) referenced by the Milestone 1 event contract and the
Milestone 2 interface contract table.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class FaultReportIn(BaseModel):
    """Inbound event: what a reporter submits."""

    equipment_id: str = Field(..., min_length=3, max_length=32)
    location: str = Field(..., min_length=2, max_length=120)
    description: str = Field(..., min_length=5, max_length=500)
    severity: Severity
    reporter_id: str = Field(..., min_length=3, max_length=32)

    @field_validator("equipment_id")
    @classmethod
    def equipment_id_format(cls, v: str) -> str:
        # Synthetic format rule: e.g. "LAB-014", "AC-203" -- letters/digits/hyphen only
        import re

        if not re.fullmatch(r"[A-Za-z0-9\-]+", v):
            raise ValueError("equipment_id must contain only letters, digits and hyphens")
        return v.upper()


class FaultReportOut(BaseModel):
    """Persisted / returned ticket record."""

    ticket_id: str
    correlation_id: str
    equipment_id: str
    location: str
    description: str
    severity: Severity
    priority: str
    status: str
    reporter_id: str
    created_at: datetime
    notified: bool


class ErrorResponse(BaseModel):
    error: str
    detail: str
    correlation_id: str
