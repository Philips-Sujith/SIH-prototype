"""
ClimateGuard India - Heat Index & WBGT Calculation Engine
Implements standardized thermal stress algorithms for early-warning heatwave detection.
"""

import math
from typing import Dict, Any


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9.0 / 5.0) + 32.0


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32.0) * 5.0 / 9.0


def calculate_heat_index(temp_c: float, rh: float) -> float:
    """
    Calculate Heat Index using NOAA Rothfusz regression.
    Takes dry-bulb temperature in °C and relative humidity in %.
    Returns Heat Index in °C rounded to 1 decimal place.

    Rothfusz regression equation (applied to °F, then converted back to °C):
    HI = -42.379 + 2.04901523*T + 10.14333127*RH
         - 0.22475541*T*RH - 0.00683783*T*T - 0.05481717*RH*RH
         + 0.00122874*T*T*RH + 0.00085282*T*RH*RH - 0.00000199*T*T*RH*RH
    """
    t_f = celsius_to_fahrenheit(temp_c)
    
    # Standard Rothfusz regression polynomial
    hi_f = (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 0.00683783 * (t_f ** 2)
        - 0.05481717 * (rh ** 2)
        + 0.00122874 * (t_f ** 2) * rh
        + 0.00085282 * t_f * (rh ** 2)
        - 0.00000199 * (t_f ** 2) * (rh ** 2)
    )

    hi_c = fahrenheit_to_celsius(hi_f)
    return round(hi_c, 1)


import logging

logger = logging.getLogger("climateguard.thermal")


def calculate_natural_wet_bulb(temp_c: float, rh: float) -> float:
    """
    Calculate natural wet-bulb temperature (Twb in °C) using Stull's (2011) psychrometric equation.
    Accurate to within 1°C for relative humidity between 5% and 99% and temperatures
    between -20°C and 50°C.
    """
    t = float(temp_c)
    r = max(1.0, min(100.0, float(rh)))
    twb = (
        t * math.atan(0.151977 * math.pow(r + 8.313659, 0.5))
        + math.atan(t + r)
        - math.atan(r - 1.676331)
        + 0.00391838 * math.pow(r, 1.5) * math.atan(0.023101 * r)
        - 4.686035
    )
    return twb


def calculate_wbgt(
    temp_c: float,
    rh: float,
    wind_speed_mps: float = 0.0,
    solar_radiation_wm2: float = 0.0
) -> float:
    """
    Calculate Wet-Bulb Globe Temperature (WBGT) in °C.
    
    Standard biometeorological formulation:
    - Outdoors under solar load (G > 10 W/m²): WBGT = 0.7 * Twb + 0.2 * Tg + 0.1 * Tdb
    - Indoors / nighttime / shade (G <= 10 W/m²): WBGT = 0.7 * Twb + 0.3 * Tdb
    
    Where:
    - Twb is natural wet-bulb temperature derived psychrometrically via Stull (2011).
    - Tg is black globe temperature estimated from ambient dry-bulb temperature,
      incoming solar irradiance (G in W/m²), and convective wind cooling (v in m/s):
      Tg = Tdb + min(15.0, (0.012 * G) / (1.0 + 0.05 * v))
      When G <= 10 W/m² (nighttime), Tg = Tdb, naturally converging to 0.7*Twb + 0.3*Tdb.
    """
    temp_c = float(temp_c)
    rh = max(1.0, min(100.0, float(rh)))
    wind = max(0.0, float(wind_speed_mps))
    solar = max(0.0, float(solar_radiation_wm2)) if solar_radiation_wm2 is not None else 0.0

    twb = calculate_natural_wet_bulb(temp_c, rh)

    if solar > 10.0:
        wind_damping = 1.0 + 0.05 * wind
        delta_tg = min(15.0, (0.012 * solar) / wind_damping)
        tg = temp_c + delta_tg
        wbgt_raw = 0.7 * twb + 0.2 * tg + 0.1 * temp_c
    else:
        wbgt_raw = 0.7 * twb + 0.3 * temp_c

    # Evaporative cooling wind adjustment (0.05°C per m/s above 2 m/s, capped at -2.0°C)
    wind_damping = 0.0
    if wind > 2.0:
        wind_damping = min(2.0, 0.05 * (wind - 2.0))

    wbgt_final = wbgt_raw - wind_damping
    return round(wbgt_final, 1)


def get_risk_category(wbgt_c: float) -> Dict[str, Any]:
    """
    Determine risk category, color, and severity level based on WBGT (°C):
    < 28       -> Low (Green)
    28 <= < 30 -> Caution (Yellow)
    30 <= < 32 -> Danger (Orange)
    32 <= < 35 -> Extreme Danger (Red)
    >= 35      -> Severe (Dark Red)
    """
    if wbgt_c < 28.0:
        return {
            "category": "Low",
            "level": "low",
            "color": "#10b981",  # Green
            "weight": 1,
            "description": "Normal activity permitted. Ensure standard hydration."
        }
    elif wbgt_c < 30.0:
        return {
            "category": "Caution",
            "level": "caution",
            "color": "#f59e0b",  # Yellow
            "weight": 2,
            "description": "Fatigue possible with prolonged exposure. Provide shade and regular water breaks."
        }
    elif wbgt_c < 32.0:
        return {
            "category": "Danger",
            "level": "danger",
            "color": "#f97316",  # Orange
            "weight": 3,
            "description": "Heat cramps and heat exhaustion likely. Restrict strenuous outdoor work between 12 PM - 4 PM."
        }
    elif wbgt_c <= 35.0:
        return {
            "category": "Extreme Danger",
            "level": "extreme",
            "color": "#ef4444",  # Red
            "weight": 4,
            "description": "Heat stroke imminent with continued exposure. Activate municipal cooling stations and emergency alerts."
        }
    else:
        return {
            "category": "Severe",
            "level": "severe",
            "color": "#991b1b",  # Dark Red
            "weight": 5,
            "description": "Critical emergency. Life-threatening thermal stress. Immediate cessation of non-essential outdoor labor."
        }


def calculate_risk_score(
    wbgt_c: float,
    elderly_pct: float,
    outdoor_worker_pct: float
) -> float:
    """
    Rule-based mortality/vulnerability risk score:
    risk_score = category_weight(WBGT) * (1 + 0.5*elderly_pct/100 + 0.5*outdoor_worker_pct/100)
    where category_weight is Low=1, Caution=2, Danger=3, Extreme=4, Severe=5.
    
    *Notice: Illustrative rule-based index incorporating demographic vulnerability,*
    *not an epidemiologically validated clinical model.*
    """
    cat_info = get_risk_category(wbgt_c)
    weight = cat_info["weight"]
    demographic_multiplier = 1.0 + (0.5 * (elderly_pct / 100.0)) + (0.5 * (outdoor_worker_pct / 100.0))
    score = weight * demographic_multiplier
    return round(score, 2)


def calculate_heat_stress_score(wbgt_c: float, hi_c: float, rh_pct: float) -> int:
    """
    ClimateGuard-Derived Normalized Heat Stress Score (0–100 scale).
    A deterministic decision-support indicator reflecting multidimensional thermal load:
    - WBGT (55% weight): Primary human outdoor thermal stress index
    - Heat Index (35% weight): Apparent temperature incorporating metabolic humidity load
    - Relative Humidity penalty (10% weight): Inhibitor of evaporative sweat cooling

    Baseline normalization parameters:
    - WBGT safe baseline: 22°C (0 pts), critical ceiling: 37°C (100 pts)
    - HI safe baseline: 25°C (0 pts), dangerous ceiling: 50°C (100 pts)
    - RH baseline: 30% (0 pts), saturated ceiling: 90% (100 pts)

    *Note: Designed for operational early warning decision support.*
    *Not an internationally standardized clinical index.*
    """
    wbgt_norm = max(0.0, min(100.0, ((wbgt_c - 22.0) / 15.0) * 100.0))
    hi_norm = max(0.0, min(100.0, ((hi_c - 25.0) / 25.0) * 100.0))
    rh_norm = max(0.0, min(100.0, ((rh_pct - 30.0) / 60.0) * 100.0))

    combined = (0.55 * wbgt_norm) + (0.35 * hi_norm) + (0.10 * rh_norm)
    return int(round(max(0.0, min(100.0, combined))))


def get_heat_stress_tier(score: int) -> Dict[str, str]:
    """
    Return human-readable tier and badge styling for Heat Stress Score.
    """
    if score >= 85:
        return {"tier": "CRITICAL", "color": "#991b1b"}
    elif score >= 70:
        return {"tier": "VERY HIGH", "color": "#ef4444"}
    elif score >= 55:
        return {"tier": "HIGH", "color": "#f97316"}
    elif score >= 40:
        return {"tier": "MODERATE", "color": "#f59e0b"}
    else:
        return {"tier": "LOW", "color": "#10b981"}


def estimate_tr_from_solar(temp_c: float, shortwave_radiation_wm2: float = 0.0, wind_mps: float = 2.0) -> float:
    """
    Estimate Mean Radiant Temperature (Tr) from ambient dry-bulb temperature (tdb)
    and global horizontal / shortwave solar radiation (G in W/m²).

    *Note on Approximation:*
    In the absence of field globe-thermometer measurements or full 6-directional
    radiant flux sensors, outdoor mean radiant temperature is standardly approximated
    by elevating ambient air temperature proportionally to incoming solar irradiance,
    damped by convective wind cooling:
    Tr ≈ Tdb + (0.012 * G) / (1.0 + 0.05 * wind_mps)
    Under night or overcast conditions (G = 0), Tr ≈ Tdb.
    Under intense tropical South India midday sun (G ≈ 800 W/m²), Tr exceeds Tdb by ~8-10°C,
    consistent with standard biometeorological modeling and WBGT simplified assumptions.
    """
    if shortwave_radiation_wm2 is None or shortwave_radiation_wm2 <= 0.0:
        return round(float(temp_c), 1)

    wind_damping = 1.0 + 0.05 * max(0.0, float(wind_mps))
    delta_tr = (0.012 * float(shortwave_radiation_wm2)) / wind_damping
    # Cap solar radiant elevation to realistic physical limit (15°C above air temp)
    delta_tr = min(15.0, delta_tr)
    return round(float(temp_c) + delta_tr, 1)


def compute_utci(tdb: float, tr: float, v: float, rh: float) -> float:
    """
    Calculate Universal Thermal Climate Index (UTCI) in °C using
    the validated pythermalcomfort library implementing Bröde et al. (2012).

    Parameters:
    - tdb: Ambient dry-bulb air temperature (°C), valid -50°C to +50°C
    - tr: Mean radiant temperature (°C), valid delta (tr - tdb) in -30°C to +70°C
    - v: Wind speed at 10m height (m/s), valid 0.5 to 17.0 m/s
    - rh: Relative humidity (%), valid 5% to 100%

    Returns:
    - UTCI value in °C rounded to 1 decimal place.
    """
    tdb_raw = float(tdb)
    tr_raw = float(tr) if tr is not None else tdb_raw
    v_raw = float(v)
    rh_raw = float(rh)

    # Validate input boundaries according to UTCI polynomial operational domain
    out_of_bounds = []
    if v_raw < 0.5 or v_raw > 17.0:
        out_of_bounds.append(f"wind_speed={v_raw:.1f} m/s (valid 0.5-17.0 m/s)")
    diff_tr = tr_raw - tdb_raw
    if diff_tr < -30.0 or diff_tr > 70.0:
        out_of_bounds.append(f"(Tr - Tdb)={diff_tr:.1f}°C (valid -30.0 to +70.0°C)")
    if tdb_raw < -50.0 or tdb_raw > 50.0:
        out_of_bounds.append(f"Tdb={tdb_raw:.1f}°C (valid -50.0 to +50.0°C)")
    if rh_raw < 5.0 or rh_raw > 100.0:
        out_of_bounds.append(f"RH={rh_raw:.1f}% (valid 5.0 to 100.0%)")

    if out_of_bounds:
        logger.warning(
            f"UTCI input parameters out of operational bounds, clamping: {', '.join(out_of_bounds)}"
        )

    # Explicit clamping to valid operational regression envelope
    v_clean = max(0.5, min(17.0, v_raw))
    rh_clean = max(5.0, min(100.0, rh_raw))
    tdb_clean = max(-50.0, min(50.0, tdb_raw))
    clamped_diff = max(-30.0, min(70.0, diff_tr))
    tr_clean = tdb_clean + clamped_diff

    try:
        from pythermalcomfort.models.utci import utci
        res = utci(tdb=tdb_clean, tr=tr_clean, v=v_clean, rh=rh_clean, limit_inputs=False)
        val = float(res.utci if hasattr(res, 'utci') else res)
        return round(val, 1)
    except Exception as exc:
        logger.error(f"pythermalcomfort utci error, falling back to approximation: {exc}")
        # Fallback approximation: polynomial estimation if library encounters issue
        vapor_p_kpa = (rh_clean / 100.0) * 0.61078 * math.exp((17.27 * tdb_clean) / (237.3 + tdb_clean))
        delta_t_rad = tr_clean - tdb_clean
        approx = tdb_clean + (0.6075 * delta_t_rad) + (0.0288 * vapor_p_kpa * 10.0) - (0.85 * math.sqrt(v_clean))
        return round(approx, 1)


def get_utci_category(utci_c: float) -> Dict[str, Any]:
    """
    Determine UTCI stress category, severity, and color based on official UTCI thresholds:
    < 9.0        -> Cold Stress (Floored at "No Thermal Stress" for South India tropical domain)
    9.0 - 26.0   -> No Thermal Stress (Green #10b981)
    26.0 - 32.0  -> Moderate Heat Stress (Yellow #f59e0b)
    32.0 - 38.0  -> Strong Heat Stress (Orange #f97316)
    38.0 - 46.0  -> Very Strong Heat Stress (Red #ef4444)
    >= 46.0      -> Extreme Heat Stress (Dark Red #991b1b)
    """
    if utci_c < 26.0:
        return {
            "category": "No Thermal Stress",
            "level": "none",
            "color": "#10b981",
            "weight": 1,
            "description": "No thermal stress. Comfortable environmental conditions."
        }
    elif utci_c < 32.0:
        return {
            "category": "Moderate Heat Stress",
            "level": "moderate",
            "color": "#f59e0b",
            "weight": 2,
            "description": "Moderate heat stress. Maintain hydration during prolonged activity."
        }
    elif utci_c < 38.0:
        return {
            "category": "Strong Heat Stress",
            "level": "strong",
            "color": "#f97316",
            "weight": 3,
            "description": "Strong heat stress. Noticeable physical strain and elevated perspiration."
        }
    elif utci_c < 46.0:
        return {
            "category": "Very Strong Heat Stress",
            "level": "very_strong",
            "color": "#ef4444",
            "weight": 4,
            "description": "Very strong heat stress. High risk of heat exhaustion and cramps. Seek shade."
        }
    else:
        return {
            "category": "Extreme Heat Stress",
            "level": "extreme",
            "color": "#991b1b",
            "weight": 5,
            "description": "Extreme heat stress. Severe medical emergency. Heat stroke imminent."
        }


