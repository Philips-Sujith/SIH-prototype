"""
test_telegram_alerts.py - Comprehensive QA test suite for multilingual
static alert templates and Telegram alert broadcasting service.
"""

import pytest
from alert_templates import (
    format_multilingual_alert,
    normalize_category,
    ALERT_TEMPLATES
)
from telegram_service import send_telegram_alert, get_telegram_credentials


def test_alert_templates_all_tiers_have_three_languages():
    """Verify all risk tiers contain complete templates for EN, TA, and HI."""
    required_tiers = ["Caution", "Danger", "Extreme Danger", "Severe", "Low"]
    heat_alert_tiers = ["Caution", "Danger", "Extreme Danger", "Severe"]
    required_langs = ["en", "ta", "hi"]

    for tier in required_tiers:
        assert tier in ALERT_TEMPLATES, f"Missing tier: {tier}"
        for lang in required_langs:
            template = ALERT_TEMPLATES[tier].get(lang)
            assert template, f"Missing {lang} template for tier {tier}"
            assert "{district}" in template
            assert "{time_window}" in template
            if tier in heat_alert_tiers:
                assert "{peak_start}" in template
                assert "{peak_end}" in template


def test_format_multilingual_alert_interpolation():
    """Verify parameters are accurately injected into all 3 languages."""
    result = format_multilingual_alert(
        district="Madurai",
        category="Danger",
        wbgt=31.4,
        temp=37.2,
        time_window="11:30 AM – 4:00 PM",
        peak_start="11:30 AM",
        peak_end="4:00 PM"
    )

    assert result["category"] == "Danger"
    assert result["district"] == "Madurai"
    assert "Madurai" in result["english"]
    assert "Madurai" in result["tamil"]
    assert "Madurai" in result["hindi"]
    assert "31.4°C" in result["english"]
    assert "11:30 AM" in result["english"]
    assert "4:00 PM" in result["english"]

    # Verify combined message includes all 3 language sections in order
    combined = result["combined_message"]
    pos_en = combined.find("[ENGLISH]")
    pos_ta = combined.find("[தமிழ் / TAMIL]")
    pos_hi = combined.find("[हिन्दी / HINDI]")

    assert pos_en != -1, "English section missing from combined message"
    assert pos_ta != -1, "Tamil section missing from combined message"
    assert pos_hi != -1, "Hindi section missing from combined message"
    assert pos_en < pos_ta < pos_hi, "Language sections not in order EN -> TA -> HI"


def test_category_normalization():
    """Verify various string formats map to standardized tiers."""
    assert normalize_category("Extreme") == "Extreme Danger"
    assert normalize_category("Extreme Danger") == "Extreme Danger"
    assert normalize_category("Danger") == "Danger"
    assert normalize_category("Caution") == "Caution"
    assert normalize_category("Severe") == "Severe"
    assert normalize_category("Normal") == "Low"


def test_telegram_service_missing_credentials(monkeypatch):
    """Verify graceful error reporting when credentials are missing or blank."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)

    res = send_telegram_alert("Test alert message")
    assert res["sent"] is False
    assert "not configured" in res["error"].lower()


def test_telegram_service_invalid_channel(monkeypatch):
    """Verify graceful error reporting when Telegram returns an error."""
    # Retain bot token, but use a nonexistent channel
    res = send_telegram_alert("Test alert message", chat_id="@nonexistent_channel_xyz_998877")
    assert res["sent"] is False
    assert "error" in res
    assert len(res["error"]) > 0


def test_alert_endpoint_test_modes():
    """Verify Alert Test Mode applies designated test tier parameters without altering live data."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # 1. Caution test mode
    r_caution = client.post("/api/alert", json={"district_id": "chennai", "test_mode": "caution"})
    assert r_caution.status_code == 200
    d_c = r_caution.json()
    assert d_c["is_test_mode"] is True
    assert d_c["test_mode"] == "caution"
    assert d_c["thermal_category"] == "Caution"
    assert d_c["wbgt"] == 28.5
    assert d_c["temp"] == 34.0
    assert "28.5°C" in d_c["languages"]["en"]

    # 2. Danger test mode
    r_danger = client.post("/api/alert", json={"district_id": "chennai", "test_mode": "danger"})
    assert r_danger.status_code == 200
    d_d = r_danger.json()
    assert d_d["is_test_mode"] is True
    assert d_d["thermal_category"] == "Danger"
    assert d_d["wbgt"] == 30.5
    assert d_d["temp"] == 37.0
    assert "30.5°C" in d_d["languages"]["en"]

    # 3. Extreme test mode
    r_extreme = client.post("/api/alert", json={"district_id": "chennai", "test_mode": "extreme"})
    assert r_extreme.status_code == 200
    d_e = r_extreme.json()
    assert d_e["is_test_mode"] is True
    assert d_e["thermal_category"] == "Extreme Danger"
    assert d_e["wbgt"] == 33.0
    assert d_e["temp"] == 40.0
    assert "33.0°C" in d_e["languages"]["en"]

    # 4. Severe test mode
    r_severe = client.post("/api/alert", json={"district_id": "chennai", "test_mode": "severe"})
    assert r_severe.status_code == 200
    d_s = r_severe.json()
    assert d_s["is_test_mode"] is True
    assert d_s["thermal_category"] == "Severe"
    assert d_s["wbgt"] == 36.0
    assert d_s["temp"] == 43.0
    assert "36.0°C" in d_s["languages"]["en"]

    # 5. Live Data mode (default)
    r_live = client.post("/api/alert", json={"district_id": "chennai", "test_mode": "live"})
    assert r_live.status_code == 200
    d_l = r_live.json()
    assert d_l["is_test_mode"] is False
    assert d_l["test_mode"] == "live"

