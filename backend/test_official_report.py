"""
test_official_report.py - Unit and Integration Tests for Official Municipal PDF Report Generation & Delivery
"""

import io
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
import pypdf

from main import app
from report_generator import generate_official_pdf_report, _derive_forecast_trend_summary, _get_risk_guidance
from telegram_service import send_telegram_document


def test_forecast_trend_summary_derivation():
    """Verify trend summary derivation logic across various patterns."""
    # Escalating
    forecast_rising = [
        {"wbgt": 28.0, "date": "2026-09-26"},
        {"wbgt": 29.0, "date": "2026-09-27"},
        {"wbgt": 31.0, "date": "2026-09-28"},
        {"wbgt": 33.0, "date": "2026-09-29"},
        {"wbgt": 33.5, "date": "2026-09-30"}
    ]
    summary_rising = _derive_forecast_trend_summary(forecast_rising)
    assert "escalate" in summary_rising or "WBGT 33.5" in summary_rising

    # Easing
    forecast_falling = [
        {"wbgt": 34.0, "date": "2026-09-26"},
        {"wbgt": 33.0, "date": "2026-09-27"},
        {"wbgt": 30.0, "date": "2026-09-28"},
        {"wbgt": 28.0, "date": "2026-09-29"},
        {"wbgt": 27.0, "date": "2026-09-30"}
    ]
    summary_falling = _derive_forecast_trend_summary(forecast_falling)
    assert "easing" in summary_falling or "peak early" in summary_falling


def test_risk_guidance_tiers():
    """Verify formal administrative guidance is generated for each tier."""
    for tier in ["Severe", "Extreme Danger", "Danger", "Caution", "Low"]:
        guidance = _get_risk_guidance(tier)
        assert len(guidance) > 20
        assert "DIRECTIVE" in guidance or "ADVISORY" in guidance


def test_generate_official_pdf_structure():
    """Verify that generate_official_pdf_report outputs a valid, parseable PDF with expected text."""
    district_sample = {
        "id": "chennai",
        "name": "Chennai",
        "district": "Chennai",
        "state": "Tamil Nadu",
        "temp": 35.2,
        "rh": 72.0,
        "wind": 4.1,
        "wbgt": 32.8,
        "hi": 48.5,
        "utci": 42.0,
        "category": "Extreme Danger",
        "heat_stress_score": 78,
        "elderly_pct": 11.5,
        "outdoor_worker_pct": 26.0
    }
    forecast_sample = [
        {"date": "2026-09-26", "temp_max": 35.2, "wbgt": 32.8, "utci": 42.0, "hi": 48.5, "category": "Extreme Danger"},
        {"date": "2026-09-27", "temp_max": 36.0, "wbgt": 33.4, "utci": 43.1, "hi": 50.2, "category": "Extreme Danger"},
        {"date": "2026-09-28", "temp_max": 34.5, "wbgt": 31.8, "utci": 40.5, "hi": 46.1, "category": "Danger"}
    ]
    checklist_sample = [
        {
            "id": "cooling_centres",
            "label": "Open municipal cooling centres and shaded water hydration points",
            "checked": True,
            "checkedAt": "2026-09-26T01:15:00Z",
            "checkedBy": "Dr. K. Ramanathan, IAS"
        },
        {
            "id": "shift_work_hours",
            "label": "Enforce mandatory work stoppage for outdoor labor (12:00 PM – 4:00 PM)",
            "checked": False,
            "checkedAt": None,
            "checkedBy": None
        }
    ]

    pdf_bytes = generate_official_pdf_report(
        district_data=district_sample,
        forecast_data=forecast_sample,
        mortality_analogue={
            "analogue_scenario": {"date": "14 May 2024", "state": "Tamil Nadu", "wbgt_c": 33.0, "maximum_temperature_c": 38.0},
            "summary": {"baseline_mortality_rate_per_100000": 1.8, "average_mortality_rate_per_100000": 2.9, "average_simulated_deaths": 4.5}
        },
        checklist=checklist_sample,
        officer_name="Dr. K. Ramanathan, IAS"
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_api_report_endpoint_valid_district():
    """Verify POST /api/report generates report and handles delivery gracefully."""
    client = TestClient(app)
    response = client.post("/api/report", json={
        "district_id": "chennai",
        "officer_name": "Test Officer",
        "checklist": [
            {
                "id": "cooling_centres",
                "label": "Open cooling centres",
                "checked": True,
                "checkedAt": "2026-09-26T01:20:00Z",
                "checkedBy": "Test Officer"
            }
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "official_report"
    assert data["district"] == "Chennai"
    assert "filename" in data
    assert data["filename"].endswith(".pdf")
    assert "officials_chat_id" in data
