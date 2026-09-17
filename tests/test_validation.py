"""
Unit tests for the validation rules -- Milestone 3 Evidence E5 (invalid
input rejected) starts here at the function level, before it's proven
again at the API level in test_api.py.
"""
import pytest
from pydantic import ValidationError

from app.schemas import FaultReportIn, Severity
from app.processing import derive_priority


VALID_PAYLOAD = {
    "equipment_id": "LAB-014",
    "location": "Science Building, Room 214",
    "description": "Projector will not power on.",
    "severity": "high",
    "reporter_id": "STU-2026-001",
}


def test_valid_report_parses():
    report = FaultReportIn(**VALID_PAYLOAD)
    assert report.equipment_id == "LAB-014"
    assert report.severity == Severity.high


def test_missing_required_field_rejected():
    bad = dict(VALID_PAYLOAD)
    del bad["description"]
    with pytest.raises(ValidationError):
        FaultReportIn(**bad)


def test_invalid_severity_rejected():
    bad = dict(VALID_PAYLOAD, severity="catastrophic")
    with pytest.raises(ValidationError):
        FaultReportIn(**bad)


def test_malformed_equipment_id_rejected():
    bad = dict(VALID_PAYLOAD, equipment_id="LAB 014!!")
    with pytest.raises(ValidationError):
        FaultReportIn(**bad)


def test_equipment_id_is_normalised_to_uppercase():
    report = FaultReportIn(**dict(VALID_PAYLOAD, equipment_id="lab-014"))
    assert report.equipment_id == "LAB-014"


@pytest.mark.parametrize(
    "severity,expected_priority",
    [
        (Severity.high, "P1"),
        (Severity.medium, "P2"),
        (Severity.low, "P3"),
    ],
)
def test_priority_derivation(severity, expected_priority):
    assert derive_priority(severity) == expected_priority
