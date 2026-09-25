"""
Unit tests for heat_index.py core thermal algorithms.
"""

import pytest
from heat_index import (
    calculate_heat_index,
    calculate_wbgt,
    get_risk_category,
    calculate_risk_score,
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
)


def test_temperature_conversions():
    assert celsius_to_fahrenheit(0) == 32.0
    assert celsius_to_fahrenheit(100) == 212.0
    assert fahrenheit_to_celsius(32.0) == 0.0
    assert fahrenheit_to_celsius(212.0) == 100.0


def test_heat_index_extreme():
    # 40°C and 70% RH is extreme heatwave conditions in India
    hi = calculate_heat_index(40.0, 70.0)
    # NOAA Rothfusz regression should report severe heat index (> 55°C)
    assert hi > 55.0


def test_heat_index_moderate():
    # 30°C and 50% RH
    hi = calculate_heat_index(30.0, 50.0)
    # Typically around 31-34°C
    assert 30.0 <= hi <= 35.0


def test_wbgt_and_risk_categories():
    # Mild weather: 22°C, 40% RH
    wbgt_mild = calculate_wbgt(22.0, 40.0, wind_speed_mps=1.0)
    assert wbgt_mild < 28.0
    cat_mild = get_risk_category(wbgt_mild)
    assert cat_mild["category"] == "Low"
    assert cat_mild["weight"] == 1

    # Severe heat: 40°C, 70% RH
    wbgt_severe = calculate_wbgt(40.0, 70.0, wind_speed_mps=2.0)
    assert wbgt_severe > 35.0
    cat_severe = get_risk_category(wbgt_severe)
    assert cat_severe["category"] == "Severe"
    assert cat_severe["weight"] == 5
    assert cat_severe["color"] == "#991b1b"

    # Category boundaries
    assert get_risk_category(27.9)["category"] == "Low"
    assert get_risk_category(28.0)["category"] == "Caution"
    assert get_risk_category(29.9)["category"] == "Caution"
    assert get_risk_category(30.0)["category"] == "Danger"
    assert get_risk_category(31.9)["category"] == "Danger"
    assert get_risk_category(32.0)["category"] == "Extreme Danger"
    assert get_risk_category(35.0)["category"] == "Extreme Danger"
    assert get_risk_category(35.1)["category"] == "Severe"


def test_wind_damping():
    temp = 35.0
    rh = 60.0
    # No wind adjustment under or at 2 m/s
    wbgt_calm = calculate_wbgt(temp, rh, wind_speed_mps=2.0)
    wbgt_breeze = calculate_wbgt(temp, rh, wind_speed_mps=12.0)
    # Wind at 12 m/s -> excess = 10 m/s -> damping = 10 * 0.05 = 0.5°C
    assert round(wbgt_calm - wbgt_breeze, 1) == 0.5

    # Capped damping at 2.0°C
    wbgt_gale = calculate_wbgt(temp, rh, wind_speed_mps=50.0)
    assert round(wbgt_calm - wbgt_gale, 1) == 2.0


def test_demographic_risk_score():
    # Danger category (weight = 3), elderly=12%, outdoor_worker=28%
    # multiplier = 1 + 0.5 * 0.12 + 0.5 * 0.28 = 1 + 0.06 + 0.14 = 1.20
    # score = 3 * 1.20 = 3.60
    wbgt_danger = 31.0
    score = calculate_risk_score(wbgt_danger, elderly_pct=12.0, outdoor_worker_pct=28.0)
    assert score == 3.60


def test_utci_reference_values():
    from heat_index import compute_utci, get_utci_category, estimate_tr_from_solar

    # Documented reference condition: calm, moderate humidity 30°C
    # Should land in Moderate Heat Stress range (26 - 32°C)
    utci_mod = compute_utci(tdb=30.0, tr=30.0, v=1.0, rh=50.0)
    assert 26.0 <= utci_mod <= 32.0
    cat_mod = get_utci_category(utci_mod)
    assert cat_mod["category"] == "Moderate Heat Stress"
    assert cat_mod["color"] == "#f59e0b"

    # Comfortable / mild condition: 20°C, calm, 50% RH -> No thermal stress (< 26°C)
    utci_mild = compute_utci(tdb=20.0, tr=20.0, v=1.0, rh=50.0)
    assert utci_mild < 26.0
    cat_mild = get_utci_category(utci_mild)
    assert cat_mild["category"] == "No Thermal Stress"
    assert cat_mild["color"] == "#10b981"

    # Extreme / Strong radiant condition: 38°C with elevated Tr (48°C) under tropical solar load
    utci_severe = compute_utci(tdb=38.0, tr=48.0, v=2.0, rh=60.0)
    assert utci_severe >= 38.0
    cat_severe = get_utci_category(utci_severe)
    assert cat_severe["category"] in ["Very Strong Heat Stress", "Extreme Heat Stress"]


def test_utci_threshold_boundaries():
    from heat_index import get_utci_category

    assert get_utci_category(25.9)["category"] == "No Thermal Stress"
    assert get_utci_category(26.0)["category"] == "Moderate Heat Stress"
    assert get_utci_category(31.9)["category"] == "Moderate Heat Stress"
    assert get_utci_category(32.0)["category"] == "Strong Heat Stress"
    assert get_utci_category(37.9)["category"] == "Strong Heat Stress"
    assert get_utci_category(38.0)["category"] == "Very Strong Heat Stress"
    assert get_utci_category(45.9)["category"] == "Very Strong Heat Stress"
    assert get_utci_category(46.0)["category"] == "Extreme Heat Stress"


def test_estimate_tr_from_solar():
    from heat_index import estimate_tr_from_solar

    # Night or overcast (G = 0) -> Tr == Tdb
    assert estimate_tr_from_solar(32.0, 0.0) == 32.0
    assert estimate_tr_from_solar(32.0, None) == 32.0

    # Sunny day: 800 W/m² solar load at 2 m/s wind
    # Tr should be elevated by ~8-10°C
    tr_sunny = estimate_tr_from_solar(32.0, 800.0, wind_mps=2.0)
    assert 38.0 <= tr_sunny <= 45.0


def test_nighttime_wbgt_and_solar_handling():
    """
    Verify that at nighttime (solar_radiation = 0), WBGT does not produce false
    high-risk alarms and converges to natural psychrometric wet-bulb + dry-bulb blend.
    """
    from heat_index import calculate_wbgt, get_risk_category

    # Typical coastal South India night (Chennai at 8 PM): 28.5°C, 74% RH, 3.5 m/s wind, 0 solar
    wbgt_night = calculate_wbgt(28.5, 74.0, wind_speed_mps=3.5, solar_radiation_wm2=0.0)
    # Natural wet bulb is ~24.8°C; WBGT = 0.7*24.8 + 0.3*28.5 - 0.025 ≈ 25.9°C
    assert wbgt_night < 28.0
    risk_night = get_risk_category(wbgt_night)
    assert risk_night["category"] == "Low"
    assert risk_night["level"] == "low"

    # Same air temp and humidity during direct midday tropical sun (G = 850 W/m²)
    wbgt_day = calculate_wbgt(28.5, 74.0, wind_speed_mps=3.5, solar_radiation_wm2=850.0)
    assert wbgt_day > wbgt_night
    assert wbgt_day >= 27.5


def test_utci_input_clamping_and_warnings(caplog):
    """
    Verify that compute_utci gracefully clamps extreme or out-of-range inputs
    and logs a warning instead of producing unphysical values or crashing.
    """
    import logging
    from heat_index import compute_utci

    with caplog.at_level(logging.WARNING):
        # Extreme hurricane wind speed (35 m/s) and high Tr delta (80°C)
        val = compute_utci(tdb=32.0, tr=120.0, v=35.0, rh=70.0)
        # Should clamp wind to 17 m/s and Tr-Tdb to 70°C without crashing
        assert isinstance(val, float)
        assert any("UTCI input parameters out of operational bounds" in record.message for record in caplog.records)


