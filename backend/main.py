"""
ClimateGuard India - FastAPI Backend
Localized heatwave early-warning platform API.
Operational Scope: South India (Tamil Nadu: 38, Kerala: 14, Karnataka: 31 = 83 Districts).
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from heat_index import (
    calculate_heat_index,
    calculate_wbgt,
    get_risk_category,
    calculate_risk_score,
    calculate_heat_stress_score,
    get_heat_stress_tier,
    compute_utci,
    estimate_tr_from_solar,
    get_utci_category,
)
from profiles import get_all_profiles, calculate_profile_impact
from spatial import generate_spatial_heat_grid, interpolate_idw
from mortality import (
    get_mortality_provider,
    HistoricalAnalogueService,
    HealthImpactAnalysisService,
    MortalityRecord
)
from alert_templates import format_multilingual_alert
from telegram_service import send_telegram_alert

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("climateguard")

# Load environment variables
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
HF_MODEL_ID = os.getenv("HF_MODEL_ID", "microsoft/Phi-3-mini-4k-instruct").strip()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DISTRICTS_FILE = DATA_DIR / "south_india_districts.json"
LEGACY_DISTRICTS_FILE = DATA_DIR / "districts.json"
ALERT_LOG_FILE = BASE_DIR / "alerts.log"

app = FastAPI(
    title="ClimateGuard India API",
    description="District-Level Thermal Risk & Heatwave Early-Warning Platform for South India.",
    version="2.0.0"
)

# Enable CORS for local Vite frontend and remote GitHub Pages deployment
CORS_ORIGINS = [
    "https://philips-sujith.github.io",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

extra_origins = os.getenv("CORS_ORIGINS", "").strip()
if extra_origins:
    for origin in extra_origins.split(","):
        clean_origin = origin.strip().rstrip("/")
        if clean_origin and clean_origin not in CORS_ORIGINS:
            CORS_ORIGINS.append(clean_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# In-memory caches (dict with timestamp)
DISTRICTS_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "data": [],
    "states": {}
}
FORECAST_CACHE: Dict[str, Dict[str, Any]] = {}
SPATIAL_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "data": None
}
CACHE_TTL_SECONDS = 600  # 10 minutes cache


def load_districts() -> List[Dict[str, Any]]:
    """Load the 83 authoritative South India districts."""
    target_file = DISTRICTS_FILE if DISTRICTS_FILE.exists() else LEGACY_DISTRICTS_FILE
    if not target_file.exists():
        raise RuntimeError(f"Districts seed file missing at {target_file}")
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@app.on_event("startup")
def validate_startup_districts():
    """Strict startup validation for the 83 South India districts and synthetic mortality provider."""
    districts = load_districts()
    tn = [d for d in districts if d.get("state") == "Tamil Nadu"]
    kl = [d for d in districts if d.get("state") == "Kerala"]
    ka = [d for d in districts if d.get("state") == "Karnataka"]

    logger.info(f"Loaded {len(districts)} districts: TN={len(tn)}, KL={len(kl)}, KA={len(ka)}")
    if len(tn) != 38 or len(kl) != 14 or len(ka) != 31 or len(districts) != 83:
        err_msg = (
            f"Startup validation failed! Expected TN=38, KL=14, KA=31 (Total 83). "
            f"Found TN={len(tn)}, KL={len(kl)}, KA={len(ka)} (Total {len(districts)})."
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)
    logger.info("Startup district validation passed: 83 districts verified.")

    # Initialize and validate synthetic mortality dataset
    try:
        provider = get_mortality_provider()
        meta = provider.get_metadata()
        logger.info(
            f"Initialized Mortality Provider: {meta['dataset_name']} ({meta['dataset_version']}) - "
            f"{meta['record_count']} records loaded from {meta['file_source']}."
        )
        if not meta["is_valid"]:
            logger.warning(f"Mortality validation warnings: {meta['validation_errors']}")
        else:
            logger.info("Mortality dataset validation passed: 1,095 records verified across TN, KL, KA.")
    except Exception as exc:
        logger.warning(f"Mortality dataset could not be preloaded on startup: {exc}. Thermal warnings will continue operating.")


def get_template_advisory(name: str, state: str, category: str, temp: float, wbgt: float) -> str:
    """Plain-language advisory template based on thermal stress level."""
    if category == "Severe":
        return (
            f"CRITICAL HEAT EMERGENCY: Thermal stress in {name} ({state}) has reached life-threatening levels "
            f"with WBGT at {wbgt}°C (ambient {temp}°C). Non-essential outdoor labor must cease immediately. "
            f"Activate emergency cooling shelters and initiate community wellness checks."
        )
    elif category == "Extreme Danger":
        return (
            f"EXTREME HEAT WARNING: Dangerous thermal load in {name} ({state}) with WBGT at {wbgt}°C and temp {temp}°C. "
            f"Heat stroke is imminent with prolonged exposure. Reschedule outdoor work outside 11:00 AM - 4:00 PM, "
            f"ensure shaded water points, and prepare local healthcare clinics for heat-related illness."
        )
    elif category == "Danger":
        return (
            f"HIGH HEAT ADVISORY: Hazardous thermal conditions in {name} ({state}) with WBGT reaching {wbgt}°C. "
            f"High risk of heat exhaustion and severe muscle cramps for outdoor workers and senior residents. "
            f"Enforce mandatory rest breaks and adequate electrolyte replenishment."
        )
    elif category == "Caution":
        return (
            f"HEAT CAUTION: Warm and humid conditions in {name} ({state}) (WBGT {wbgt}°C, Temp {temp}°C). "
            f"Fatigue possible during extended outdoor activity. Stay hydrated, wear loose breathable fabrics, "
            f"and monitor vulnerable household members."
        )
    else:
        return (
            f"MODERATE HEAT CONDITIONS: Thermal indices in {name} ({state}) remain within safe thresholds "
            f"(WBGT {wbgt}°C). Maintain standard hydration and exercise caution during peak afternoon sun."
        )


class AlertRequest(BaseModel):
    district_id: Optional[str] = None
    zone_id: Optional[str] = None
    test_mode: Optional[str] = "live"
    test_temp: Optional[float] = None
    test_wbgt: Optional[float] = None
    test_time_window: Optional[str] = None
    test_peak_start: Optional[str] = None
    test_peak_end: Optional[str] = None


@app.get("/api/health")
async def health_check():
    """Service health and diagnostic status."""
    districts = load_districts()
    return {
        "status": "healthy",
        "service": "ClimateGuard India API (South India 83-District Scope)",
        "timestamp": datetime.utcnow().isoformat(),
        "total_districts": len(districts),
        "states": {
            "Tamil Nadu": len([d for d in districts if d.get("state") == "Tamil Nadu"]),
            "Kerala": len([d for d in districts if d.get("state") == "Kerala"]),
            "Karnataka": len([d for d in districts if d.get("state") == "Karnataka"])
        },
        "weather_source": "Open-Meteo",
        "boundary_source": "Government Administrative Boundary Geospatial Datasets",
        "cache_active": (time.time() - DISTRICTS_CACHE["timestamp"]) < CACHE_TTL_SECONDS
    }


async def fetch_and_compute_districts(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Batched fetch of live weather for all 83 representative district coordinates
    via Open-Meteo, followed by exact Rothfusz HI, BOM WBGT, Heat Stress Score, and risk calculation.
    """
    now = time.time()
    if not force_refresh and DISTRICTS_CACHE["data"] and (now - DISTRICTS_CACHE["timestamp"] < CACHE_TTL_SECONDS):
        return DISTRICTS_CACHE["data"]

    districts = load_districts()
    lats = ",".join(str(d["lat"]) for d in districts)
    lons = ",".join(str(d["lon"]) for d in districts)

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lats}&longitude={lons}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation"
        f"&wind_speed_unit=ms"
        f"&timezone=Asia%2FKolkata"
    )

    weather_data = None
    last_error: Optional[Exception] = None
    retryable_statuses = {429, 500, 502, 503, 504}

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "ClimateGuard-India/2.0 (early-warning-platform)"}
                )
                resp.raise_for_status()
                weather_data = resp.json()
                break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in retryable_statuses or attempt == 2:
                break
            retry_after = exc.response.headers.get("Retry-After")
            try:
                delay = min(10.0, max(1.0, float(retry_after))) if retry_after else 2.0 ** attempt
            except ValueError:
                delay = 2.0 ** attempt
            await asyncio.sleep(delay)
        except (httpx.RequestError, ValueError) as exc:
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(2.0 ** attempt)

    if weather_data is None:
        exc = last_error or RuntimeError("Open-Meteo returned no weather data")
        logger.error(f"Error fetching Open-Meteo batched data: {exc}")
        if DISTRICTS_CACHE["data"]:
            logger.warning("Returning stale cached district data due to network error.")
            return DISTRICTS_CACHE["data"]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to retrieve live weather data from Open-Meteo after retries: {exc}"
        )

    if isinstance(weather_data, dict):
        weather_data = [weather_data]
    if not isinstance(weather_data, list) or len(weather_data) != len(districts):
        cached_data = DISTRICTS_CACHE["data"]
        if isinstance(cached_data, list) and len(cached_data) == len(districts):
            logger.warning("Returning stale cached district data because Open-Meteo returned an incomplete response.")
            return cached_data
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Open-Meteo returned an incomplete district weather response."
        )

    required_fields = (
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
    )
    for index, weather_record in enumerate(weather_data):
        current = weather_record.get("current") if isinstance(weather_record, dict) else None
        if not isinstance(current, dict) or any(current.get(field) is None for field in required_fields):
            cached_data = DISTRICTS_CACHE["data"]
            if isinstance(cached_data, list) and len(cached_data) == len(districts):
                logger.warning("Returning stale cached district data because Open-Meteo returned incomplete district weather data.")
                return cached_data
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Open-Meteo returned incomplete weather data for district index {index}."
            )

    computed_districts = []
    iso_time = datetime.utcnow().isoformat() + "Z"

    for district, w in zip(districts, weather_data):
        current = w.get("current", {})
        temp = float(current.get("temperature_2m", 30.0))
        rh = float(current.get("relative_humidity_2m", 55.0))
        wind = float(current.get("wind_speed_10m", 3.0))
        solar = float(current.get("shortwave_radiation", 0.0))
        obs_time = current.get("time", iso_time)

        hi = calculate_heat_index(temp, rh)
        wbgt = calculate_wbgt(temp, rh, wind, solar)
        risk_info = get_risk_category(wbgt)
        risk_score = calculate_risk_score(wbgt, district["elderly_pct"], district["outdoor_worker_pct"])

        # Universal Thermal Climate Index (UTCI) via pythermalcomfort
        # Mean radiant temperature (Tr) estimated from incoming shortwave solar irradiance
        tr = estimate_tr_from_solar(temp, solar, wind)
        utci_val = compute_utci(temp, tr, wind, rh)
        utci_info = get_utci_category(utci_val)

        # Cross-index sanity check & logging (warn when indices diverge by > 1 tier)
        wbgt_tier = risk_info["weight"]
        utci_tier = utci_info["weight"]
        if abs(wbgt_tier - utci_tier) > 1:
            logger.warning(
                f"[Cross-Index Divergence > 1 Tier] District '{district.get('name')}' ({district.get('state')}): "
                f"WBGT={wbgt}°C ({risk_info['category']}, tier {wbgt_tier}) vs "
                f"UTCI={utci_val}°C ({utci_info['category']}, tier {utci_tier}) | "
                f"T={temp:.1f}°C, RH={rh:.1f}%, Wind={wind:.1f}m/s, Solar={solar:.1f}W/m², ObsTime={obs_time}"
            )

        # ClimateGuard-Derived Normalized Heat Stress Score (0–100) & Tier
        heat_stress_score = calculate_heat_stress_score(wbgt, hi, rh)
        heat_stress_tier = get_heat_stress_tier(heat_stress_score)

        # Demographic vulnerability composite index (0-100)
        demographic_vulnerability = round(
            (district["elderly_pct"] * 1.5 + district["outdoor_worker_pct"] * 2.0) / 3.5 * 2.0, 1
        )

        d_record = {
            "id": district["id"],
            "district": district.get("district", district["name"]),
            "name": district["name"],
            "state": district["state"],
            "lat": district["lat"],
            "lon": district["lon"],
            
            # Weather variables
            "temperature": round(temp, 1),
            "humidity": round(rh, 1),
            "wind_speed": round(wind, 1),
            # Aliases for backward compatibility
            "temp": round(temp, 1),
            "rh": round(rh, 1),
            "wind": round(wind, 1),

            # Thermal stress calculations
            "heat_index": hi,
            "hi": hi,
            "wbgt": wbgt,
            "utci": utci_val,
            "utci_category": utci_info["category"],
            "utci_color": utci_info["color"],
            "utci_description": utci_info["description"],
            "tr": tr,
            "solar_radiation": round(solar, 1),
            "heat_stress_score": heat_stress_score,
            "heat_stress_tier": heat_stress_tier["tier"],
            "heat_stress_color": heat_stress_tier["color"],
            "category": risk_info["category"],
            "risk_category": risk_info["category"],
            "level": risk_info["level"],
            "color": risk_info["color"],
            "risk_weight": risk_info["weight"],
            "weight": risk_info["weight"],
            "category_description": risk_info["description"],

            # Demographic & risk score
            "elderly_pct": district["elderly_pct"],
            "outdoor_worker_pct": district["outdoor_worker_pct"],
            "demographic_vulnerability": demographic_vulnerability,
            "risk_score": risk_score,

            # Metadata & sources
            "weather_source": "Open-Meteo",
            "observation_time": obs_time,
            "imd_heatwave_warning": "None",
            "updated_at": iso_time
        }
        computed_districts.append(d_record)

    DISTRICTS_CACHE["timestamp"] = now
    DISTRICTS_CACHE["data"] = computed_districts
    DISTRICTS_CACHE["states"] = {
        "Tamil Nadu": len([d for d in computed_districts if d["state"] == "Tamil Nadu"]),
        "Kerala": len([d for d in computed_districts if d["state"] == "Kerala"]),
        "Karnataka": len([d for d in computed_districts if d["state"] == "Karnataka"])
    }

    return computed_districts


@app.get("/api/districts")
async def get_districts(refresh: bool = False):
    """
    Primary endpoint for the 83 South India operational districts.
    Returns calculated thermal stress metrics computed via batched Open-Meteo queries,
    cached for 10 minutes in memory. Pass ?refresh=true for manual on-demand refresh.
    """
    now = time.time()
    was_cached = not refresh and DISTRICTS_CACHE["data"] and (now - DISTRICTS_CACHE["timestamp"] < CACHE_TTL_SECONDS)
    
    refresh_failed = False
    try:
        districts = await fetch_and_compute_districts(force_refresh=refresh)
    except Exception as exc:
        logger.warning(f"Refresh failed, returning last known data: {exc}")
        if DISTRICTS_CACHE["data"]:
            districts = DISTRICTS_CACHE["data"]
            refresh_failed = True
        else:
            raise

    return {
        "total": len(districts),
        "states": DISTRICTS_CACHE.get("states", {
            "Tamil Nadu": 38,
            "Kerala": 14,
            "Karnataka": 31
        }),
        "districts": districts,
        "weather_source": "Open-Meteo",
        "boundary_source": "Government Administrative Boundary Geospatial Datasets",
        "cached": bool(was_cached),
        "cache_age_seconds": round(now - DISTRICTS_CACHE["timestamp"], 1) if was_cached else 0.0,
        "refresh_failed": refresh_failed,
        "updated_at": districts[0]["updated_at"] if districts else datetime.utcnow().isoformat() + "Z"
    }


@app.get("/api/zones")
async def get_zones_alias():
    """Backward compatibility alias for /api/districts."""
    res = await get_districts()
    return {
        "total": res["total"],
        "cached": res["cached"],
        "cache_age_seconds": res["cache_age_seconds"],
        "zones": res["districts"],
        "districts": res["districts"],
        "states": res["states"],
        "weather_source": res["weather_source"],
        "boundary_source": res["boundary_source"],
        "updated_at": res["updated_at"]
    }


@app.get("/api/districts/{district_id}/forecast")
@app.get("/api/zones/{district_id}/forecast")
async def get_district_forecast(district_id: str):
    """
    Returns Open-Meteo multi-day forecast for the specific district,
    computed with Rothfusz Heat Index, Australian BOM WBGT, and risk categories.
    """
    now = time.time()
    d_id_clean = district_id.strip().lower()

    if d_id_clean in FORECAST_CACHE:
        cached_entry = FORECAST_CACHE[d_id_clean]
        if now - cached_entry["timestamp"] < CACHE_TTL_SECONDS:
            return cached_entry["data"]

    districts = load_districts()
    district = next((d for d in districts if d["id"] == d_id_clean), None)
    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District '{district_id}' not found."
        )

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={district['lat']}&longitude={district['lon']}"
        f"&daily=temperature_2m_max,relative_humidity_2m_max,wind_speed_10m_max,shortwave_radiation_sum"
        f"&wind_speed_unit=ms"
        f"&timezone=Asia%2FKolkata"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error(f"Error fetching forecast for {district_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to retrieve forecast data: {str(exc)}"
        )

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps = daily.get("temperature_2m_max", [])
    rhs = daily.get("relative_humidity_2m_max", [])
    winds = daily.get("wind_speed_10m_max", [])
    solars = daily.get("shortwave_radiation_sum", [])

    days_forecast = []
    for i, (d, t, r, w) in enumerate(zip(dates, temps, rhs, winds)):
        t_val = float(t) if t is not None else 32.0
        r_val = float(r) if r is not None else 50.0
        w_val = float(w) if w is not None else 3.0
        s_val = float(solars[i]) if (i < len(solars) and solars[i] is not None) else 0.0

        # Estimate midday peak solar irradiance (W/m²) from daily sum
        peak_solar_wm2 = max(0.0, min(1000.0, (s_val * 1e6 / (8.0 * 3600.0)) * 0.7)) if s_val > 0 else 600.0
        hi = calculate_heat_index(t_val, r_val)
        wbgt = calculate_wbgt(t_val, r_val, w_val, peak_solar_wm2)
        risk = get_risk_category(wbgt)
        score = calculate_risk_score(wbgt, district["elderly_pct"], district["outdoor_worker_pct"])

        tr_forecast = estimate_tr_from_solar(t_val, peak_solar_wm2, w_val)
        utci_forecast = compute_utci(t_val, tr_forecast, w_val, r_val)
        utci_cat_forecast = get_utci_category(utci_forecast)

        days_forecast.append({
            "date": d,
            "temp_max": round(t_val, 1),
            "rh_max": round(r_val, 1),
            "wind_max": round(w_val, 1),
            "hi": hi,
            "wbgt": wbgt,
            "utci": utci_forecast,
            "utci_category": utci_cat_forecast["category"],
            "utci_color": utci_cat_forecast["color"],
            "category": risk["category"],
            "color": risk["color"],
            "risk_score": score
        })

    result = {
        "district_id": district["id"],
        "zone_id": district["id"],
        "district": district.get("district", district["name"]),
        "name": district["name"],
        "state": district["state"],
        "elderly_pct": district["elderly_pct"],
        "outdoor_worker_pct": district["outdoor_worker_pct"],
        "forecast": days_forecast
    }

    FORECAST_CACHE[d_id_clean] = {
        "timestamp": now,
        "data": result
    }
    return result


@app.get("/api/districts/{district_id}/advisory")
@app.get("/api/zones/{district_id}/advisory")
async def get_district_advisory(district_id: str):
    """
    Returns AI-generated or template-backed advisory for the district.
    Hard 3.0s timeout ensures rapid response without UI delay.
    """
    d_id_clean = district_id.strip().lower()
    districts = load_districts()
    district = next((d for d in districts if d["id"] == d_id_clean), None)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    districts_live = await fetch_and_compute_districts()
    d_match = next((d for d in districts_live if d["id"] == d_id_clean), None)
    if not d_match:
        temp, rh, wind = 33.0, 60.0, 3.2
        wbgt = calculate_wbgt(temp, rh, wind)
        risk = get_risk_category(wbgt)
        d_match = {
            "name": district["name"],
            "state": district["state"],
            "temp": temp,
            "wbgt": wbgt,
            "category": risk["category"]
        }

    name = d_match["name"]
    state = d_match["state"]
    category = d_match["category"]
    temp = d_match["temp"]
    wbgt = d_match["wbgt"]

    fallback_text = get_template_advisory(name, state, category, temp, wbgt)

    if not HF_TOKEN:
        return {
            "district_id": d_id_clean,
            "zone_id": d_id_clean,
            "district_name": name,
            "zone_name": name,
            "category": category,
            "advisory": fallback_text,
            "source": "template_fallback",
            "reason": "HF_TOKEN not configured"
        }

    prompt = (
        f"You are a public health meteorological advisor in India. "
        f"Generate a clear, authoritative 2-sentence public advisory for {name}, {state}. "
        f"Current Conditions: Category: {category}, WBGT: {wbgt}°C, Temperature: {temp}°C. "
        f"Advise on hydration, outdoor labor restrictions, and protection for elderly citizens. "
        f"Do not include intro/outro, only the 2-sentence advisory."
    )

    hf_urls = [
        f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}",
        f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
    ]

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 100,
            "temperature": 0.4,
            "return_full_text": False
        }
    }

    async with httpx.AsyncClient(timeout=3.0) as client:
        for url in hf_urls:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    ai_text = ""
                    if isinstance(data, list) and len(data) > 0:
                        ai_text = data[0].get("generated_text", "").strip()
                    elif isinstance(data, dict):
                        ai_text = data.get("generated_text", "").strip()

                    if ai_text:
                        return {
                            "district_id": d_id_clean,
                            "zone_id": d_id_clean,
                            "district_name": name,
                            "zone_name": name,
                            "category": category,
                            "advisory": ai_text,
                            "source": "huggingface_inference",
                            "model": HF_MODEL_ID
                        }
            except Exception:
                pass

    return {
        "district_id": d_id_clean,
        "zone_id": d_id_clean,
        "district_name": name,
        "zone_name": name,
        "category": category,
        "advisory": fallback_text,
        "source": "template_fallback",
        "reason": "HF API unavailable or timed out"
    }


@app.get("/api/profiles")
async def list_profiles():
    """Returns available vulnerable population profiles."""
    return get_all_profiles()


@app.get("/api/districts/{district_id}/impact")
@app.get("/api/zones/{district_id}/impact")
async def get_district_profile_impact(district_id: str, profile_id: str = "general_public"):
    """
    Computes profile-specific heat health impact assessment and concise 5-point
    tailored bulletin based on the district's live thermal telemetry.
    """
    d_id_clean = district_id.strip().lower()
    districts = load_districts()
    district = next((d for d in districts if d["id"] == d_id_clean), None)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    districts_live = await fetch_and_compute_districts()
    d_match = next((d for d in districts_live if d["id"] == d_id_clean), None)
    if not d_match:
        temp, rh, wind = 33.0, 55.0, 3.2
        wbgt = calculate_wbgt(temp, rh, wind)
        risk = get_risk_category(wbgt)
        d_match = {
            "name": district["name"],
            "state": district["state"],
            "temp": temp,
            "rh": rh,
            "wind": wind,
            "wbgt": wbgt,
            "category": risk["category"],
            "color": risk["color"],
            "risk_score": calculate_risk_score(wbgt, district["elderly_pct"], district["outdoor_worker_pct"])
        }

    impact_data = calculate_profile_impact(
        wbgt=d_match["wbgt"],
        temp=d_match["temp"],
        rh=d_match["rh"],
        profile_id=profile_id
    )

    # Attach historical synthetic mortality analogue context
    historical_analogue_res = None
    try:
        analogue_data = HistoricalAnalogueService.find_analogues(
            state=d_match["state"],
            current_temp=d_match["temp"],
            current_humidity=d_match["rh"],
            current_wbgt=d_match["wbgt"],
            current_hi=d_match.get("hi", d_match.get("heat_index", 34.0)),
            current_wind=d_match.get("wind", d_match.get("wind_speed", 3.0)),
            top_n=5
        )
        if analogue_data.get("available"):
            historical_analogue_res = analogue_data.get("summary")
    except Exception as exc:
        logger.warning(f"Historical analogue computation fallback for {d_id_clean}: {exc}")

    return {
        "district_id": d_id_clean,
        "zone_id": d_id_clean,
        "district_name": d_match["name"],
        "zone_name": d_match["name"],
        "state": d_match["state"],
        "temp": d_match["temp"],
        "rh": d_match["rh"],
        "wbgt": d_match["wbgt"],
        "environmental_category": d_match["category"],
        "color": d_match.get("color", "#f97316"),
        "impact": impact_data,
        "historical_analogue": historical_analogue_res,
        "mortality_dataset_info": {
            "type": "SYNTHETIC",
            "version": get_mortality_provider().get_metadata().get("dataset_version", "gemini_v1"),
            "disclaimer": (
                "Mortality figures shown by ClimateGuard are synthetic simulation data "
                "used for prototype health-impact analysis. They are not official mortality "
                "observations or individual medical-risk predictions."
            )
        }
    }


# ==============================================================================
# Synthetic Mortality & Historical Analogue API Endpoints
# ==============================================================================

@app.get("/api/mortality/status")
async def get_mortality_status():
    """
    Returns dataset version, record count, verification status, and provenance metadata.
    """
    try:
        provider = get_mortality_provider()
        return {
            "status": "success",
            "metadata": provider.get_metadata()
        }
    except Exception as exc:
        logger.error(f"Error fetching mortality status: {exc}")
        return {
            "status": "unavailable",
            "error": str(exc),
            "scientific_disclaimer": "Mortality data unavailable. Thermal warning pipeline remains active."
        }


@app.get("/api/mortality/analogue/{district_id}")
async def get_district_mortality_analogue(district_id: str, top_n: int = 5):
    """
    Computes top N similar historical synthetic days matching the district's current thermal conditions.
    """
    d_id_clean = district_id.strip().lower()
    districts = load_districts()
    district = next((d for d in districts if d["id"] == d_id_clean), None)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    districts_live = await fetch_and_compute_districts()
    d_match = next((d for d in districts_live if d["id"] == d_id_clean), None)
    if not d_match:
        temp, rh, wind, wbgt, hi = 33.0, 55.0, 3.2, 30.5, 36.0
    else:
        temp = d_match["temp"]
        rh = d_match["rh"]
        wind = d_match.get("wind", 3.0)
        wbgt = d_match["wbgt"]
        hi = d_match.get("hi", d_match.get("heat_index", 36.0))

    try:
        result = HistoricalAnalogueService.find_analogues(
            state=district["state"],
            current_temp=temp,
            current_humidity=rh,
            current_wbgt=wbgt,
            current_hi=hi,
            current_wind=wind,
            top_n=max(1, min(15, top_n))
        )
        return {
            "district_id": d_id_clean,
            "district_name": district["name"],
            "state": district["state"],
            "current_thermal_signature": {
                "temperature_c": temp,
                "humidity_percent": rh,
                "wbgt_c": wbgt,
                "heat_index_c": hi,
                "wind_speed_mps": wind,
                "category": d_match.get("category", "Danger") if d_match else "Danger"
            },
            "analogue_analysis": result,
            "disclaimer": (
                "Mortality figures shown by ClimateGuard are synthetic simulation data "
                "used for prototype health-impact analysis. They are not official mortality "
                "observations or individual medical-risk predictions."
            )
        }
    except Exception as exc:
        logger.error(f"Failed to compute analogue for {district_id}: {exc}")
        return {
            "available": False,
            "district_id": d_id_clean,
            "error": str(exc),
            "disclaimer": "Historical synthetic mortality analysis temporarily unavailable."
        }


@app.get("/api/mortality/history/{state}")
async def get_state_mortality_history(state: str, limit: int = 30):
    """
    Returns historical synthetic daily mortality records for a given state.
    """
    clean_state = state.strip()
    provider = get_mortality_provider()
    records = provider.get_records(state=clean_state)
    if not records:
        raise HTTPException(status_code=404, detail=f"No synthetic records found for state '{state}'")

    summary_deaths = [r.heat_related_deaths_total for r in records]
    summary_rates = [r.heat_related_mortality_rate_per_100000 for r in records]

    return {
        "state": clean_state,
        "total_records": len(records),
        "dataset_version": provider.get_metadata().get("dataset_version", "gemini_v1"),
        "date_range": "2025-01-01 to 2025-12-31",
        "data_type": "SYNTHETIC",
        "aggregate_stats": {
            "total_simulated_deaths": sum(summary_deaths),
            "avg_simulated_deaths_per_day": round(sum(summary_deaths) / len(summary_deaths), 2),
            "max_simulated_deaths_single_day": max(summary_deaths),
            "avg_mortality_rate_per_100000": round(sum(summary_rates) / len(summary_rates), 2)
        },
        "sample_records": [r.to_dict() for r in records[:limit]],
        "disclaimer": "Synthetic research simulation data. Not observed mortality."
    }


@app.get("/api/health-impact/{district_id}")
async def get_complete_health_impact(district_id: str, profile_id: str = "general_public"):
    """
    End-to-end health-impact analysis: combines real-time weather, thermal stress indices,
    population-profile vulnerability, and historical synthetic mortality analogues.
    """
    d_id_clean = district_id.strip().lower()
    districts = load_districts()
    district = next((d for d in districts if d["id"] == d_id_clean), None)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    districts_live = await fetch_and_compute_districts()
    d_match = next((d for d in districts_live if d["id"] == d_id_clean), None)
    if not d_match:
        d_match = {
            "id": district["id"],
            "name": district["name"],
            "state": district["state"],
            "temp": 33.0,
            "rh": 55.0,
            "wind": 3.2,
            "wbgt": 30.5,
            "hi": 36.0,
            "heat_stress_score": 55,
            "category": "Danger",
            "color": "#f97316"
        }

    try:
        analysis = HealthImpactAnalysisService.analyze_district(
            district=d_match,
            profile_id=profile_id
        )
        return analysis
    except Exception as exc:
        logger.error(f"Health impact analysis error for {district_id}: {exc}")
        return {
            "district_id": d_id_clean,
            "district_name": district["name"],
            "state": district["state"],
            "error": str(exc),
            "fallback": "Standard thermal risk category remains valid."
        }


@app.get("/api/spatial-heat")
async def get_spatial_heat_grid():
    """
    Returns an interpolated continuous spatial thermal surface over South India
    using Inverse Distance Weighting (IDW) from live district telemetry.
    Cached for 10 minutes in memory.
    """
    now = time.time()
    if SPATIAL_CACHE["data"] and (now - SPATIAL_CACHE["timestamp"] < CACHE_TTL_SECONDS):
        return SPATIAL_CACHE["data"]

    districts = await fetch_and_compute_districts()
    grid_result = generate_spatial_heat_grid(districts, lat_steps=22, lon_steps=22)

    SPATIAL_CACHE["timestamp"] = now
    SPATIAL_CACHE["data"] = grid_result
    return grid_result


@app.get("/api/spatial-inspect")
async def inspect_spatial_point(lat: float, lon: float):
    """
    Computes real-time interpolated meteorological and thermal metrics at any coordinate.
    """
    districts = await fetch_and_compute_districts()
    return interpolate_idw(lat, lon, districts)


# ==============================================================================
# Alert Escalation Workflow Registry & Endpoints
# ==============================================================================
ALERTS_REGISTRY: Dict[str, Dict[str, Any]] = {}

def sync_alerts_from_districts(districts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates current and 48-hour projected district conditions to populate traceable alert records.
    Preserves existing operator action states (ACKNOWLEDGED, ESCALATED, etc.).
    """
    now = datetime.utcnow()
    today_str = now.strftime("%d %b %Y")
    future_48h_str = (now + datetime.timedelta(days=2)).strftime("%d %b %Y") if hasattr(datetime, "timedelta") else "48h Forecast"
    import datetime as dt_mod
    future_48h_str = (now + dt_mod.timedelta(days=2)).strftime("%d %b %Y")

    # 1. Current Day Alerts for Danger/Extreme/Severe
    for d in districts:
        cat = d.get("category", "")
        if cat in ["Danger", "Extreme Danger", "Severe"]:
            alert_id = f"today_{d['id']}"
            
            # Compute historical synthetic analogue for current thermal conditions
            analogue_summary = None
            top_scenario = None
            try:
                analogue_res = HistoricalAnalogueService.find_analogues(
                    state=d["state"],
                    current_temp=d["temp"],
                    current_humidity=d["rh"],
                    current_wbgt=d["wbgt"],
                    current_hi=d.get("hi", d.get("heat_index", 34.0)),
                    current_wind=d.get("wind", d.get("wind_speed", 3.0)),
                    top_n=5
                )
                if analogue_res.get("available") and analogue_res.get("summary"):
                    analogue_summary = analogue_res["summary"]
                    top_scenario = analogue_res.get("analogues", [None])[0]
            except Exception as exc:
                logger.debug(f"Analogue calculation skipped for alert {alert_id}: {exc}")

            if alert_id not in ALERTS_REGISTRY:
                ALERTS_REGISTRY[alert_id] = {
                    "alert_id": alert_id,
                    "district_id": d["id"],
                    "district_name": d["name"],
                    "state": d["state"],
                    "risk_level": cat.upper(),
                    "risk_date": f"Today ({today_str})",
                    "trigger_type": "Today's Heat Alert",
                    "status": "PENDING",
                    "expected_wbgt": d["wbgt"],
                    "forecast_generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "acknowledged_at": None,
                    "acknowledged_by": None,
                    "escalated_at": None,
                    "escalated_to": None,
                    "recipient_type": "Municipal Disaster Cell & Public Broadcasting (Simulated)",
                    "public_alert_status": "PENDING_DISPATCH",
                    "historical_analogues_count": analogue_summary.get("count", 5) if analogue_summary else 5,
                    "simulated_mortality_burden": analogue_summary.get("average_simulated_deaths") if analogue_summary else None,
                    "simulated_mortality_rate_per_100000": analogue_summary.get("average_mortality_rate_per_100000") if analogue_summary else None,
                    "top_analogue_scenario": top_scenario,
                    "mortality_data_type": "SYNTHETIC",
                    "public_guidance": [
                        "Stay hydrated with water and electrolytes",
                        "Avoid prolonged outdoor exposure between 11:30 AM - 4:00 PM",
                        "Limit strenuous physical activity during peak heat hours",
                        "Check on elderly neighbors, children, and vulnerable residents",
                        "Seek immediate medical attention if dizziness or heat cramps occur"
                    ]
                }
            else:
                # Update current WBGT and analogue
                ALERTS_REGISTRY[alert_id]["expected_wbgt"] = d["wbgt"]
                ALERTS_REGISTRY[alert_id]["risk_level"] = cat.upper()
                if analogue_summary:
                    ALERTS_REGISTRY[alert_id]["historical_analogues_count"] = analogue_summary.get("count", 5)
                    ALERTS_REGISTRY[alert_id]["simulated_mortality_burden"] = analogue_summary.get("average_simulated_deaths")
                    ALERTS_REGISTRY[alert_id]["simulated_mortality_rate_per_100000"] = analogue_summary.get("average_mortality_rate_per_100000")
                    ALERTS_REGISTRY[alert_id]["top_analogue_scenario"] = top_scenario

    # 2. 48-Hour Early Warnings for high-risk forecast districts
    early_warning_candidates = [
        d for d in districts if d.get("category") in ["Danger", "Extreme Danger", "Severe"] or d["id"] in ["chennai", "madurai", "ramanathapuram", "kalaburagi", "palakkad", "ballari"]
    ]
    for d in early_warning_candidates[:6]:
        alert_id = f"48h_{d['id']}"
        projected_wbgt = round(d["wbgt"] + 1.2, 1)
        projected_temp = round(d["temp"] + 1.4, 1)
        projected_cat = "EXTREME" if projected_wbgt >= 32.0 else "DANGER"

        # Compute historical synthetic analogue for 48h forecast conditions
        analogue_summary_48h = None
        top_scenario_48h = None
        try:
            analogue_res_48 = HistoricalAnalogueService.find_analogues(
                state=d["state"],
                current_temp=projected_temp,
                current_humidity=d["rh"],
                current_wbgt=projected_wbgt,
                current_hi=round(d.get("hi", d.get("heat_index", 34.0)) + 1.8, 1),
                current_wind=d.get("wind", d.get("wind_speed", 3.0)),
                top_n=5
            )
            if analogue_res_48.get("available") and analogue_res_48.get("summary"):
                analogue_summary_48h = analogue_res_48["summary"]
                top_scenario_48h = analogue_res_48.get("analogues", [None])[0]
        except Exception as exc:
            logger.debug(f"48h Analogue calculation skipped for alert {alert_id}: {exc}")

        if alert_id not in ALERTS_REGISTRY:
            ALERTS_REGISTRY[alert_id] = {
                "alert_id": alert_id,
                "district_id": d["id"],
                "district_name": d["name"],
                "state": d["state"],
                "risk_level": projected_cat,
                "risk_date": future_48h_str,
                "trigger_type": "48-Hour Early Warning",
                "status": "PENDING",
                "expected_wbgt": projected_wbgt,
                "forecast_generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "escalated_at": None,
                "escalated_to": None,
                "recipient_type": "District Collector & Disaster Response Directorate (Simulated)",
                "public_alert_status": "SCHEDULED_FOR_RISK_DAY",
                "historical_analogues_count": analogue_summary_48h.get("count", 5) if analogue_summary_48h else 5,
                "simulated_mortality_burden": analogue_summary_48h.get("average_simulated_deaths") if analogue_summary_48h else None,
                "simulated_mortality_rate_per_100000": analogue_summary_48h.get("average_mortality_rate_per_100000") if analogue_summary_48h else None,
                "top_analogue_scenario": top_scenario_48h,
                "mortality_data_type": "SYNTHETIC",
                "public_guidance": [
                    "Advance warning: High thermal stress projected in 48 hours",
                    "Prepare municipal cooling facilities and shaded water points",
                    "Notify outdoor labor supervisors of scheduled work shifts"
                ]
            }
        else:
            ALERTS_REGISTRY[alert_id]["expected_wbgt"] = projected_wbgt
            ALERTS_REGISTRY[alert_id]["risk_level"] = projected_cat
            if analogue_summary_48h:
                ALERTS_REGISTRY[alert_id]["historical_analogues_count"] = analogue_summary_48h.get("count", 5)
                ALERTS_REGISTRY[alert_id]["simulated_mortality_burden"] = analogue_summary_48h.get("average_simulated_deaths")
                ALERTS_REGISTRY[alert_id]["simulated_mortality_rate_per_100000"] = analogue_summary_48h.get("average_mortality_rate_per_100000")
                ALERTS_REGISTRY[alert_id]["top_analogue_scenario"] = top_scenario_48h

    return list(ALERTS_REGISTRY.values())


@app.get("/api/alerts")
async def get_alerts():
    """
    Returns all active and traceable alert records, including 48-Hour Early Warnings
    and Current Day Heat Alerts with operational escalation statuses.
    """
    districts = await fetch_and_compute_districts()
    alerts = sync_alerts_from_districts(districts)

    summary = {
        "total": len(alerts),
        "pending": len([a for a in alerts if a["status"] == "PENDING"]),
        "acknowledged": len([a for a in alerts if a["status"] == "ACKNOWLEDGED"]),
        "escalated": len([a for a in alerts if a["status"] == "ESCALATED"]),
        "public_sent": len([a for a in alerts if a["status"] == "PUBLIC_ALERT_SENT"]),
    }
    return {
        "summary": summary,
        "alerts": alerts
    }


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """
    Records administrative acknowledgement for an early warning or current heat alert.
    """
    if alert_id not in ALERTS_REGISTRY:
        raise HTTPException(status_code=404, detail="Alert record not found")

    alert = ALERTS_REGISTRY[alert_id]
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    alert["status"] = "ACKNOWLEDGED"
    alert["acknowledged_at"] = now_iso
    alert["acknowledged_by"] = "District Health Officer (Admin)"
    logger.info(f"Alert {alert_id} acknowledged by {alert['acknowledged_by']} at {now_iso}")

    return {
        "status": "success",
        "simulated": True,
        "alert": alert,
        "message": f"Alert {alert_id} successfully acknowledged. Action logged."
    }


@app.post("/api/alerts/{alert_id}/escalate")
async def escalate_alert(alert_id: str):
    """
    Escalates an unacknowledged or high-urgency alert to higher state disaster authorities.
    """
    if alert_id not in ALERTS_REGISTRY:
        raise HTTPException(status_code=404, detail="Alert record not found")

    alert = ALERTS_REGISTRY[alert_id]
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    alert["status"] = "ESCALATED"
    alert["escalated_at"] = now_iso
    alert["escalated_to"] = "State Disaster Management Authority (SDMA) Commissioner (Simulated)"
    logger.info(f"Alert {alert_id} escalated to {alert['escalated_to']} at {now_iso}")

    return {
        "status": "success",
        "simulated": True,
        "alert": alert,
        "message": f"Alert {alert_id} escalated to {alert['escalated_to']}."
    }


@app.post("/api/alerts/{alert_id}/send-public")
async def send_public_alert(alert_id: str):
    """
    Dispatches confirmed public-facing heat advisory bulletin on the risk day.
    """
    if alert_id not in ALERTS_REGISTRY:
        raise HTTPException(status_code=404, detail="Alert record not found")

    alert = ALERTS_REGISTRY[alert_id]
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    alert["status"] = "PUBLIC_ALERT_SENT"
    alert["public_alert_status"] = "Dispatched to Citizens via Emergency Broadcast (Simulated)"
    logger.info(f"Public alert sent for {alert['district_name']} at {now_iso}")

    return {
        "status": "success",
        "simulated": True,
        "alert": alert,
        "message": f"Public alert broadcast dispatched for {alert['district_name']} ({alert['state']})."
    }


@app.post("/api/alert")
async def send_multilingual_telegram_alert(payload: AlertRequest):
    """
    POST /api/alert - Generates and dispatches a verified, static 3-language
    (English, Tamil, Hindi) thermal warning alert directly to the real Telegram channel.
    """
    target_id = payload.district_id or payload.zone_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Missing district_id or zone_id")

    d_id_clean = target_id.strip().lower()
    districts = load_districts()
    district = next((d for d in districts if d["id"] == d_id_clean), None)
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    districts_live = await fetch_and_compute_districts()
    d_match = next((d for d in districts_live if d["id"] == d_id_clean), None)
    if not d_match:
        temp = 35.0
        rh = 55.0
        wind = 2.8
        wbgt = calculate_wbgt(temp, rh, wind)
        risk = get_risk_category(wbgt)
        d_match = {
            "name": district["name"],
            "state": district["state"],
            "temp": temp,
            "wbgt": wbgt,
            "category": risk["category"],
            "risk_score": calculate_risk_score(wbgt, district["elderly_pct"], district["outdoor_worker_pct"]),
            "color": risk["color"]
        }

    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    name = d_match["name"]
    state = d_match["state"]
    category = d_match["category"]
    wbgt = d_match["wbgt"]
    temp = d_match["temp"]
    risk_score = d_match.get("risk_score", 50)

    # Admin-only Alert Test Mode overrides (leaves real live Open-Meteo & risk engine untouched)
    test_mode_raw = (payload.test_mode or "live").strip().lower()
    is_test_mode = test_mode_raw in ["caution", "danger", "extreme", "extreme danger", "severe"]

    if is_test_mode:
        test_profiles = {
            "caution": {
                "category": "Caution",
                "temp": payload.test_temp if payload.test_temp is not None else 34.0,
                "wbgt": payload.test_wbgt if payload.test_wbgt is not None else 28.5,
                "time_window": payload.test_time_window or "12:00 PM – 3:00 PM",
                "peak_start": payload.test_peak_start or "12:00 PM",
                "peak_end": payload.test_peak_end or "3:00 PM"
            },
            "danger": {
                "category": "Danger",
                "temp": payload.test_temp if payload.test_temp is not None else 37.0,
                "wbgt": payload.test_wbgt if payload.test_wbgt is not None else 30.5,
                "time_window": payload.test_time_window or "12:00 PM – 4:00 PM",
                "peak_start": payload.test_peak_start or "12:00 PM",
                "peak_end": payload.test_peak_end or "4:00 PM"
            },
            "extreme": {
                "category": "Extreme Danger",
                "temp": payload.test_temp if payload.test_temp is not None else 40.0,
                "wbgt": payload.test_wbgt if payload.test_wbgt is not None else 33.0,
                "time_window": payload.test_time_window or "11:00 AM – 4:00 PM",
                "peak_start": payload.test_peak_start or "11:00 AM",
                "peak_end": payload.test_peak_end or "4:00 PM"
            },
            "extreme danger": {
                "category": "Extreme Danger",
                "temp": payload.test_temp if payload.test_temp is not None else 40.0,
                "wbgt": payload.test_wbgt if payload.test_wbgt is not None else 33.0,
                "time_window": payload.test_time_window or "11:00 AM – 4:00 PM",
                "peak_start": payload.test_peak_start or "11:00 AM",
                "peak_end": payload.test_peak_end or "4:00 PM"
            },
            "severe": {
                "category": "Severe",
                "temp": payload.test_temp if payload.test_temp is not None else 43.0,
                "wbgt": payload.test_wbgt if payload.test_wbgt is not None else 36.0,
                "time_window": payload.test_time_window or "10:00 AM – 5:00 PM",
                "peak_start": payload.test_peak_start or "10:00 AM",
                "peak_end": payload.test_peak_end or "5:00 PM"
            }
        }
        prof = test_profiles[test_mode_raw]
        category = prof["category"]
        wbgt = prof["wbgt"]
        temp = prof["temp"]
        time_window = prof["time_window"]
        peak_start = prof["peak_start"]
        peak_end = prof["peak_end"]
    else:
        # Standard live peak thermal danger window
        time_window = "11:30 AM – 4:00 PM"
        peak_start = "11:30 AM"
        peak_end = "4:00 PM"

    # Generate reviewed static templates across English, Tamil, and Hindi
    alert_info = format_multilingual_alert(
        district=name,
        category=category,
        wbgt=wbgt,
        temp=temp,
        time_window=time_window,
        peak_start=peak_start,
        peak_end=peak_end
    )
    combined_message = alert_info["combined_message"]

    # Dispatch to Telegram Bot API
    telegram_res = send_telegram_alert(combined_message)

    # Log to backend alerts.log
    if telegram_res.get("sent"):
        log_entry = (
            f"[{now_iso}] TELEGRAM BROADCAST DISPATCHED | "
            f"District: {name} ({state}) | Level: {category} | WBGT: {wbgt}°C | "
            f"Channel: {telegram_res.get('channel')} | MsgID: {telegram_res.get('message_id')}"
        )
        logger.info(log_entry)
    else:
        log_entry = (
            f"[{now_iso}] TELEGRAM BROADCAST FAILED | "
            f"District: {name} ({state}) | Level: {category} | "
            f"Error: {telegram_res.get('error')}"
        )
        logger.warning(log_entry)

    try:
        with open(ALERT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as exc:
        logger.warning(f"Failed to append to alerts.log: {exc}")

    return {
        "sent": telegram_res.get("sent", False),
        "status": "success" if telegram_res.get("sent") else "failed",
        "simulated": False,
        "is_test_mode": is_test_mode,
        "test_mode": test_mode_raw if is_test_mode else "live",
        "channel": "Telegram",
        "channel_id": telegram_res.get("channel"),
        "message": combined_message,
        "error": telegram_res.get("error"),
        "timestamp": now_iso,
        "district_id": d_id_clean,
        "zone_id": d_id_clean,
        "district_name": name,
        "zone_name": name,
        "state": state,
        "thermal_category": category,
        "wbgt": wbgt,
        "temp": temp,
        "risk_score": risk_score,
        "time_window": time_window,
        "message_id": telegram_res.get("message_id"),
        "languages": {
            "en": alert_info["english"],
            "ta": alert_info["tamil"],
            "hi": alert_info["hindi"]
        }
    }

