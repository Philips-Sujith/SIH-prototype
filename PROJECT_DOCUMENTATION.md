# ClimateGuard India — Project Documentation

---

## 1. Project Overview

**ClimateGuard India** is a localized district-level heatwave early-warning platform prototype engineered to transform raw meteorological data into standardized human thermal-stress indices (NOAA Rothfusz Heat Index, Australian Bureau of Meteorology Outdoor WBGT with convective wind adjustment, and the ClimateGuard Normalized Heat Stress Score) across all **83 districts** of South India: **Tamil Nadu (38 districts)**, **Kerala (14 districts)**, and **Karnataka (31 districts)**. Operating without nationwide interpolation or coarse statewide averages, the platform renders a true district-level thermal choropleth using authoritative Indian administrative boundaries, powered by batched Open-Meteo queries against mathematically verified interior representative points cached for 10 minutes. The interface follows a high-contrast dark-mode terminal aesthetic with a balanced 58% (content) / 42% (choropleth) desktop grid, featuring two operational views: a **Public Dashboard** with an isolated scrollable demographic impact bulletin (9 vulnerable profiles), clean telemetry cards, an on-demand manual refresh button with stale-data fallback, and a conditional profile-specific Health Action Plan; and an **Admin Dashboard** equipping disaster management authorities with high-risk district groupings (Severe, Extreme, Danger), 7-day forecast trajectories, and a traceable multi-state Alert Escalation Workflow (48-Hour Early Warnings, Admin Acknowledgements, Failure-to-Act Escalations, and Risk-Day Public Alerts) with transparent simulation safeguards.

---

## 2. Tech Stack and Exact Versions

The prototype is built strictly using the locked specifications without heavy third-party UI component libraries:

### Backend Services
| Technology | Exact Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.11.9` | Primary runtime environment |
| **FastAPI** | `0.141.1` | High-performance asynchronous REST API framework |
| **Uvicorn** | `0.52.4` | ASGI server implementation for FastAPI |
| **HTTPX** | `0.28.1` | Async HTTP client for outbound Open-Meteo & HF requests |
| **Pydantic** | `2.13.5` | Data validation, parsing, and payload schema enforcement |
| **python-dotenv** | `1.2.3` | Parsing environment variables from `.env` |
| **pytest** | `9.1.1` | Automated test runner for thermal stress algorithms |

### Frontend Application
| Technology | Exact Version | Purpose |
| :--- | :--- | :--- |
| **Node.js** | `v24.13.0` | Frontend runtime engine |
| **npm** | `11.6.2` | Package manager |
| **React** | `19.2.4` | UI component library |
| **React DOM** | `19.2.4` | DOM renderer for React |
| **Vite** | `8.3.0` | Ultra-fast build tool and local dev server |
| **Leaflet** | `1.9.4` | Interactive mapping engine |
| **React Leaflet** | `5.0.0` | React wrapper bindings for Leaflet elements |
| **Chart.js** | `4.5.1` | Canvas-based multi-day forecast charting engine |
| **React Chartjs 2** | `5.3.1` | React components for Chart.js |
| **Lucide React** | `1.16.0` | Clean geometric icons for dashboard chrome |
| **Vanilla CSS** | Standard CSS3 | Custom dark-mode design system (no Tailwind, zero heavy UI frameworks) |

### External APIs
- **Open-Meteo Weather API**: `https://api.open-meteo.com/v1/forecast` (Free, keyless, real-time current telemetry and 7-day daily forecasts).
- **Hugging Face Inference API**: `https://router.huggingface.co/hf-inference/models/` and `https://api-inference.huggingface.co/models/` (AI-assisted advisory synthesis with 3.0-second hard timeout and deterministic template fallback).

---

## 3. Complete File & Folder Structure

```
y:\Projects\SIH/
├── .env                                # Local environment secrets and models (HF_TOKEN, HF_MODEL_ID)
├── PROJECT_DOCUMENTATION.md            # Comprehensive project architecture & operational documentation
├── backend/
│   ├── alerts.log                      # File persistence audit log for simulated civil defense alerts
│   ├── heat_index.py                   # Pure mathematical module for Rothfusz HI, BOM WBGT, Heat Stress Score
│   ├── profiles.py                     # Population profile configurations, exposure factors, & bulletin generator
│   ├── spatial.py                      # Continuous regional Inverse Distance Weighting (IDW) interpolation engine
│   ├── mortality.py                    # Synthetic mortality provider abstraction & historical analogue matching engine
│   ├── main.py                         # FastAPI application defining caching, outbound APIs, & routes
│   ├── test_heat_index.py              # Pytest unit tests for thermal index mathematical edge cases
│   ├── test_api_endpoints.py           # End-to-end integration test suite for all FastAPI endpoints
│   ├── test_mortality.py               # 15-point verification suite for synthetic mortality and analogue matching
│   └── data/
│       ├── south_india_districts.json  # 83 authoritative South India districts (38 TN, 14 KL, 31 KA)
│       ├── districts.json              # Legacy seed array of 18 representative high-risk India districts
│       └── mortality/
│           └── mortality_synthetic_daily_gemini.csv # 1,095 records (365 days x 3 states, 23 columns)
└── frontend/
    ├── index.html                      # HTML entrypoint with Inter/JetBrains Mono fonts & Leaflet styles
    ├── package.json                    # Frontend dependencies, build scripts, and dev configuration
    ├── package-lock.json               # Deterministic dependency lockfile
    ├── vite.config.js                  # Vite bundler configuration with React plugin
    ├── .gitignore                      # Git exclusion rules for node_modules and build artifacts
    ├── public/
    │   ├── favicon.svg                 # Application browser tab icon
    │   ├── india_states.geojson        # Simplified GeoJSON of Indian state boundaries
    │   └── south_india_districts.geojson # Authoritative district boundary GeoJSON for TN, KL, and KA
    └── src/
        ├── main.jsx                    # React root mounter rendering <App /> into #root
        ├── App.jsx                     # Top-level state container, route management, & global toast
        ├── App.css                     # Minimal app-level utility styles
        ├── index.css                   # Complete modern dark-mode design system & CSS variables
        └── components/
            ├── Header.jsx              # Navigation header with live status pulse and view toggle
            ├── IndiaHeatMap.jsx        # Interactive Leaflet choropleth map with SVG radial gradients and crisp boundaries
            ├── WeatherHeatVisual.jsx   # Dynamic centered SVG Sun, thermal progression, and telemetry metrics
            ├── PublicDashboard.jsx     # Public view: unclipped scrollable bulletin, clean telemetry, health action plan
            └── AdminDashboard.jsx      # Admin view: high-risk overview, right-column forecast & thermal outlook, bottom dispatch log
```

---

## 4. Backend Endpoints

All endpoints are hosted on the FastAPI backend instance (`http://127.0.0.1:8000`).

### 1. `GET /api/health`
- **Method**: `GET`
- **Path**: `/api/health`
- **Request Body**: None
- **Response Schema**:
```json
{
  "status": "healthy",
  "service": "ClimateGuard India API",
  "timestamp": "2026-09-23T18:15:00.000000",
  "hf_configured": true,
  "hf_model": "microsoft/Phi-3-mini-4k-instruct",
  "cache_active": true
}
```
- **Internal Execution Step-by-Step**:
  1. Inspects internal state timestamp against current epoch time.
  2. Verifies whether `HF_TOKEN` is loaded in memory.
  3. Returns standard diagnostic status without making outbound network requests.

---

### 2. `GET /api/districts` (and backward-compatible alias `GET /api/zones`)
- **Method**: `GET`
- **Path**: `/api/districts`
- **Query Parameter**: `refresh` (`bool`, default `false`). When `true`, forces fresh retrieval from Open-Meteo.
- **Request Body**: None
- **Response Schema**:
```json
{
  "total": 83,
  "states": {
    "Tamil Nadu": 38,
    "Kerala": 14,
    "Karnataka": 31
  },
  "cached": true,
  "cache_age_seconds": 14.2,
  "refresh_failed": false,
  "districts": [
    {
      "id": "chennai",
      "district": "Chennai",
      "name": "Chennai",
      "state": "Tamil Nadu",
      "lat": 13.0827,
      "lon": 80.2707,
      "temperature": 28.1,
      "humidity": 71.0,
      "wind_speed": 13.0,
      "heat_index": 31.0,
      "wbgt": 28.9,
      "heat_stress_score": 62,
      "heat_stress_tier": "HIGH",
      "heat_stress_color": "#f97316",
      "category": "Caution",
      "level": "caution",
      "color": "#f59e0b",
      "risk_weight": 2,
      "category_description": "Fatigue possible with prolonged exposure...",
      "elderly_pct": 10.4,
      "outdoor_worker_pct": 21.0,
      "demographic_vulnerability": 32.8,
      "risk_score": 2.31,
      "weather_source": "Open-Meteo",
      "updated_at": "2026-09-23T18:15:30.000000Z"
    }
  ],
  "weather_source": "Open-Meteo",
  "boundary_source": "Government Administrative Boundary Geospatial Datasets",
  "updated_at": "2026-09-23T18:15:30.000000Z"
}
```
- **Internal Execution Step-by-Step**:
  1. Checks `DISTRICTS_CACHE`. If `refresh=false` and cache age $< 600$s, returns cached records immediately.
  2. If cache is expired or `refresh=true`, loads 83 district representative coordinates from `backend/data/south_india_districts.json`.
  3. Batches coordinates into a single asynchronous HTTP GET request to Open-Meteo (`latitude=...&longitude=...&current=temperature_2m,relative_humidity_2m,wind_speed_10m`).
  4. Parses results and executes:
     - `calculate_heat_index(temp, rh)`: NOAA Rothfusz Apparent Temperature (°C).
     - `calculate_wbgt(temp, rh, wind)`: Outdoor Australian BOM WBGT with wind damping (°C).
     - `calculate_heat_stress_score(wbgt, hi, rh)`: Normalized 0–100 decision-support score.
     - `get_heat_stress_tier(score)`: High/Moderate/Low tiering badge.
     - `get_risk_category(wbgt)`: Environmental risk tier (Low, Caution, Danger, Extreme Danger, Severe).
     - `calculate_risk_score(wbgt, elderly, outdoor)`: Demographic vulnerability index.
  5. If the outbound request fails during an on-demand refresh, the handler catches the exception and returns the last known successful cache with `"refresh_failed": true`, preventing the UI from wiping valid telemetry.

---

### 3. `GET /api/districts/{district_id}/forecast`
- **Method**: `GET`
- **Path**: `/api/districts/{district_id}/forecast` (alias `/api/zones/{district_id}/forecast`)
- **Path Parameter**: `district_id` (case-insensitive string, e.g. `chennai`, `palakkad`, `bengaluru_urban`)
- **Request Body**: None
- **Response Schema**:
```json
{
  "district_id": "chennai",
  "district": "Chennai",
  "name": "Chennai",
  "state": "Tamil Nadu",
  "elderly_pct": 10.4,
  "outdoor_worker_pct": 21.0,
  "forecast": [
    {
      "date": "2026-09-24",
      "temp_max": 33.5,
      "rh_max": 74.0,
      "wind_max": 5.2,
      "hi": 44.1,
      "wbgt": 33.2,
      "category": "Extreme Danger",
      "color": "#ef4444",
      "risk_score": 4.62
    }
  ]
}
```
- **Internal Execution Step-by-Step**:
  1. Checks `FORECAST_CACHE[district_id]`. If valid within 600s, returns immediately.
  2. Resolves coordinates from `south_india_districts.json`; returns 404 if not found.
  3. Queries Open-Meteo daily endpoint: `daily=temperature_2m_max,relative_humidity_2m_max,wind_speed_10m_max`.
  4. Computes daily Rothfusz HI, BOM WBGT, and demographic risk score for each day of the 7-day ensemble.
  5. Caches and returns the daily trajectory array.

---

### 4. `GET /api/districts/{district_id}/advisory`
- **Method**: `GET`
- **Path**: `/api/districts/{district_id}/advisory` (alias `/api/zones/{district_id}/advisory`)
- **Path Parameter**: `district_id` (e.g. `chennai`)
- **Request Body**: None
- **Response Schema**:
```json
{
  "district_id": "chennai",
  "district_name": "Chennai",
  "category": "Danger",
  "advisory": "HIGH HEAT ADVISORY: Hazardous thermal conditions in Chennai (Tamil Nadu) with WBGT reaching 31.8°C. High risk of heat exhaustion and severe muscle cramps for outdoor workers and senior residents. Enforce mandatory rest breaks and adequate electrolyte replenishment.",
  "source": "template_fallback",
  "reason": "HF inference unavailable or timed out (>3s)"
}
```
- **Internal Execution Step-by-Step**:
  1. Finds district telemetry from cache.
  2. Generates baseline template advisory via `get_template_advisory()`.
  3. If `HF_TOKEN` is configured, calls Hugging Face Inference API with a **strict 3.0-second hard timeout**.
  4. Returns AI advisory on success, or seamlessly returns verified template if timed out or errored.

---

### 5. `GET /api/profiles`
- **Method**: `GET`
- **Path**: `/api/profiles`
- **Request Body**: None
- **Response Schema**:
```json
{
  "profiles": [
    {
      "id": "it_office",
      "name": "IT / Office Worker",
      "description": "Predominantly indoor personnel with commute-time outdoor exposure and AC dependency.",
      "exposure_factor": 0.65,
      "sensitivity_factor": 0.85
    },
    {
      "id": "construction_labor",
      "name": "Construction Worker / Heavy Labor",
      "description": "High continuous physical exertion under direct solar radiation.",
      "exposure_factor": 1.45,
      "sensitivity_factor": 1.25
    }
  ]
}
```
- **Internal Execution Step-by-Step**:
  1. Returns all 9 registered population profiles with metadata and baseline multipliers.

---

### 6. `GET /api/districts/{district_id}/impact`
- **Method**: `GET`
- **Path**: `/api/districts/{district_id}/impact` (alias `/api/zones/{district_id}/impact`)
- **Query Parameter**: `profile_id` (e.g. `it_office`, `construction_labor`, `elderly`, `general_public`)
- **Response Schema**:
```json
{
  "zone_id": "chennai",
  "zone_name": "Chennai",
  "state": "Tamil Nadu",
  "temp": 28.1,
  "rh": 71.0,
  "wbgt": 28.9,
  "environmental_category": "Caution",
  "color": "#f59e0b",
  "impact": {
    "profile_id": "construction_labor",
    "profile_name": "Construction Worker / Heavy Labor",
    "profile_score": 3.62,
    "impact_level": "VERY HIGH",
    "impact_color": "#ef4444",
    "bulletin": {
      "exposure": "Extreme (Direct radiant solar exposure during peak load)",
      "main_concern": "Rapid dehydration, severe muscle cramping, and heat stroke risk",
      "possible_effects": "Core body temperature elevation, mental confusion, circulatory shock",
      "recommended_action": "Mandatory 15-minute shaded rest per hour; enforce active hydration",
      "outdoor_travel": "Cease heavy outdoor scaffolding and roof work between 12:00 PM – 3:30 PM",
      "peak_period": "11:30 AM – 3:30 PM"
    }
  }
}
```
- **Internal Execution Step-by-Step**:
  1. Retrieves current telemetry for `district_id`.
  2. Evaluates `calculate_profile_impact(wbgt, temp, rh, profile_id)`.
  3. Returns tailored 6-point bulletin with exposure level, main concerns, actionable recommendations, and peak risk periods.

---

### 7. `GET /api/alerts`
- **Method**: `GET`
- **Path**: `/api/alerts`
- **Request Body**: None
- **Response Schema**:
```json
{
  "summary": {
    "total": 6,
    "pending": 4,
    "acknowledged": 1,
    "escalated": 1,
    "public_sent": 0
  },
  "alerts": [
    {
      "alert_id": "48h_chennai",
      "district_id": "chennai",
      "district_name": "Chennai",
      "state": "Tamil Nadu",
      "risk_level": "EXTREME",
      "risk_date": "2026-09-25",
      "trigger_type": "48-Hour Early Warning",
      "status": "PENDING",
      "expected_wbgt": 33.2,
      "forecast_generated_at": "2026-09-23 18:00:00 UTC",
      "acknowledged_at": null,
      "acknowledged_by": null,
      "escalated_at": null,
      "escalated_to": null,
      "recipient_type": "District Collector & Disaster Response Directorate (Simulated)",
      "public_alert_status": "SCHEDULED_FOR_RISK_DAY",
      "public_guidance": [
        "Advance warning: High thermal stress projected in 48 hours",
        "Prepare municipal cooling facilities and shaded water points",
        "Notify outdoor labor supervisors of scheduled work shifts"
      ]
    }
  ]
}
```
- **Internal Execution Step-by-Step**:
  1. Synchronizes `ALERTS_REGISTRY` against live district telemetry and 48-hour forecast projections.
  2. Aggregates summary statistics by status (`PENDING`, `ACKNOWLEDGED`, `ESCALATED`, `PUBLIC_ALERT_SENT`).
  3. Returns complete traceable alert records.

---

### 8. `POST /api/alerts/{alert_id}/acknowledge`
- **Method**: `POST`
- **Path**: `/api/alerts/{alert_id}/acknowledge`
- **Path Parameter**: `alert_id` (e.g. `48h_chennai`)
- **Request Body**: None
- **Response Schema**:
```json
{
  "status": "success",
  "simulated": true,
  "alert": {
    "alert_id": "48h_chennai",
    "status": "ACKNOWLEDGED",
    "acknowledged_at": "2026-09-23 18:18:22 UTC",
    "acknowledged_by": "District Health Officer (Admin)"
  },
  "message": "Alert 48h_chennai successfully acknowledged. Action logged."
}
```
- **Internal Execution Step-by-Step**:
  1. Verifies alert exists in `ALERTS_REGISTRY`.
  2. Sets status to `ACKNOWLEDGED`.
  3. Stamps UTC timestamp and role identifier (`District Health Officer (Admin)`).

---

### 9. `POST /api/alerts/{alert_id}/escalate`
- **Method**: `POST`
- **Path**: `/api/alerts/{alert_id}/escalate`
- **Path Parameter**: `alert_id`
- **Request Body**: None
- **Response Schema**:
```json
{
  "status": "success",
  "simulated": true,
  "alert": {
    "alert_id": "48h_chennai",
    "status": "ESCALATED",
    "escalated_at": "2026-09-23 18:19:04 UTC",
    "escalated_to": "State Disaster Management Authority (SDMA) Commissioner (Simulated)"
  },
  "message": "Alert 48h_chennai escalated to State Disaster Management Authority (SDMA) Commissioner (Simulated)."
}
```
- **Internal Execution Step-by-Step**:
  1. Verifies alert in `ALERTS_REGISTRY`.
  2. Transitions status from `PENDING` to `ESCALATED`.
  3. Records escalation timestamp and configurable recipient authority.

---

### 10. `POST /api/alerts/{alert_id}/send-public`
- **Method**: `POST`
- **Path**: `/api/alerts/{alert_id}/send-public`
- **Path Parameter**: `alert_id`
- **Request Body**: None
- **Response Schema**:
```json
{
  "status": "success",
  "simulated": true,
  "alert": {
    "alert_id": "today_chennai",
    "status": "PUBLIC_ALERT_SENT",
    "public_alert_status": "Dispatched to Citizens via Emergency Broadcast (Simulated)"
  },
  "message": "Public alert broadcast dispatched for Chennai (Tamil Nadu)."
}
```
- **Internal Execution Step-by-Step**:
  1. Validates alert and sets status to `PUBLIC_ALERT_SENT`.
  2. Marks delivery status as simulated emergency public broadcast.

---

### 11. `POST /api/alert` (Direct Emergency Dispatch Simulation)
- **Method**: `POST`
- **Path**: `/api/alert`
- **Request Body**: `{"district_id": "chennai"}`
- **Response Schema**:
```json
{
  "status": "success",
  "simulated": true,
  "timestamp": "2026-09-23 18:20:00 UTC",
  "district_name": "Chennai",
  "state": "Tamil Nadu",
  "thermal_category": "Danger",
  "wbgt": 31.8,
  "temp": 28.1,
  "risk_score": 3.42,
  "simulated_recipients": 1420,
  "channels": ["SMS (Mock)", "WhatsApp Broadcast (Mock)", "Disaster Management Cell (Mock)"],
  "message": "🚨 CLIMATEGUARD INDIA — THERMAL EARLY WARNING...",
  "delivery_note": "Simulated dispatch only. Real SMS/WhatsApp APIs are disabled in prototype mode."
}
```
- **Internal Execution Step-by-Step**:
  1. Resolves district coordinates and live telemetry.
  2. Assembles structured civil defense bulletin.
  3. Writes audit log line to `backend/alerts.log`.
  4. Returns simulated response with explicit `"simulated": true` flag.

---

### 12. `GET /api/mortality/status`
- **Method**: `GET`
- **Path**: `/api/mortality/status`
- **Request Body**: None
- **Response Schema**:
```json
{
  "status": "success",
  "metadata": {
    "dataset_name": "mortality_synthetic_daily",
    "dataset_version": "gemini_v1",
    "dataset_provider": "synthetic",
    "generated_by": "Gemini",
    "file_source": "mortality_synthetic_daily_gemini.csv",
    "date_range": "2025-01-01 to 2025-12-31",
    "states": ["Karnataka", "Kerala", "Tamil Nadu"],
    "record_count": 1095,
    "data_type": "SYNTHETIC",
    "is_valid": true,
    "validation_errors": []
  }
}
```
- **Internal Execution Step-by-Step**:
  1. Queries the singleton `MortalityDataProvider` instance.
  2. Returns full provenance metadata, row count (1,095), date range, and verification status.

---

### 13. `GET /api/mortality/analogue/{district_id}`
- **Method**: `GET`
- **Path**: `/api/mortality/analogue/{district_id}`
- **Query Parameter**: `top_n` (`int`, default `5`, max `15`).
- **Response Schema**:
```json
{
  "district_id": "virudhunagar",
  "district_name": "Virudhunagar",
  "state": "Tamil Nadu",
  "current_thermal_signature": {
    "temperature_c": 35.2,
    "humidity_percent": 61.0,
    "wbgt_c": 31.4,
    "heat_index_c": 40.1,
    "wind_speed_mps": 3.0,
    "category": "Danger"
  },
  "analogue_analysis": {
    "available": true,
    "data_type": "SYNTHETIC",
    "state_scope": "Tamil Nadu",
    "analogues": [
      {
        "date": "2025-05-18",
        "formatted_date": "18 May 2025",
        "state": "Tamil Nadu",
        "similarity_score": 94.2,
        "max_temperature_c": 38.8,
        "relative_humidity_percent": 63.0,
        "wbgt_c": 32.1,
        "heat_index_c": 41.5,
        "heatwave_day": 1,
        "heat_related_deaths_total": 4,
        "heat_related_mortality_rate_per_100000": 0.05,
        "deaths_under_30": 0,
        "deaths_30_59": 3,
        "deaths_60_plus": 1,
        "deaths_male": 3,
        "deaths_female": 1
      }
    ],
    "summary": {
      "count": 5,
      "average_similarity": 93.4,
      "min_similarity": 91.0,
      "max_similarity": 95.8,
      "average_simulated_deaths": 3.2,
      "median_simulated_deaths": 3.0,
      "min_simulated_deaths": 1,
      "max_simulated_deaths": 6,
      "average_mortality_rate_per_100000": 0.08,
      "most_affected_age_group": "Adults in Labor Force (30-59 Years)",
      "age_distribution": {
        "under_30_percent": 12.0,
        "30_59_percent": 61.0,
        "60_plus_percent": 27.0
      },
      "gender_distribution": {
        "male_percent": 58.0,
        "female_percent": 42.0
      }
    }
  },
  "disclaimer": "Mortality figures shown by ClimateGuard are synthetic simulation data used for prototype health-impact analysis. They are not official mortality observations or individual medical-risk predictions."
}
```
- **Internal Execution Step-by-Step**:
  1. Resolves district state and live meteorological telemetry.
  2. Queries `HistoricalAnalogueService.find_analogues` across the parent state's 365 daily synthetic records.
  3. Evaluates weighted normalized Euclidean distance across 6 variables.
  4. Returns top matching analogue days, similarity percentages, and demographic distributions.

---

### 14. `GET /api/mortality/history/{state}`
- **Method**: `GET`
- **Path**: `/api/mortality/history/{state}`
- **Query Parameter**: `limit` (`int`, default `30`).
- **Response Schema**:
```json
{
  "state": "Tamil Nadu",
  "total_records": 365,
  "dataset_version": "gemini_v1",
  "date_range": "2025-01-01 to 2025-12-31",
  "data_type": "SYNTHETIC",
  "aggregate_stats": {
    "total_simulated_deaths": 890,
    "avg_simulated_deaths_per_day": 2.44,
    "max_simulated_deaths_single_day": 14,
    "avg_mortality_rate_per_100000": 0.04
  },
  "sample_records": [ ... ],
  "disclaimer": "Synthetic research simulation data. Not observed mortality."
}
```
- **Internal Execution Step-by-Step**:
  1. Filters cached records by state name (`Tamil Nadu`, `Kerala`, or `Karnataka`).
  2. Computes aggregate annual simulated mortality metrics and returns sample records.

---

### 15. `GET /api/health-impact/{district_id}`
- **Method**: `GET`
- **Path**: `/api/health-impact/{district_id}`
- **Query Parameter**: `profile_id` (`str`, default `"general_public"`).
- **Response Schema**: Structured response combining live thermal conditions, historical analogues, demographic age context, and population-profile exposure guidance.

---

## 5. Every Function in Every Module

### Module: `backend/heat_index.py`

#### `celsius_to_fahrenheit(celsius: float) -> float`
- **Parameters**: `celsius` (`float`) — Temperature in °C.
- **Return Type**: `float`
- **Purpose**: Converts Celsius degrees to Fahrenheit via $(C \times 9/5) + 32$.

#### `fahrenheit_to_celsius(fahrenheit: float) -> float`
- **Parameters**: `fahrenheit` (`float`) — Temperature in °F.
- **Return Type**: `float`
- **Purpose**: Converts Fahrenheit degrees to Celsius via $(F - 32) \times 5/9$.

#### `calculate_heat_index(temp_c: float, rh: float) -> float`
- **Parameters**: `temp_c` (`float`) — Ambient dry-bulb temperature in °C; `rh` (`float`) — Relative humidity ($0\text{--}100$).
- **Return Type**: `float`
- **Purpose**: Evaluates the 9-term NOAA Rothfusz apparent temperature regression in °F, converted back to °C rounded to 1 decimal place.

#### `calculate_wbgt(temp_c: float, rh: float, wind_speed_mps: float = 0.0) -> float`
- **Parameters**: `temp_c` (`float`), `rh` (`float`), `wind_speed_mps` (`float`, default `0.0`).
- **Return Type**: `float`
- **Purpose**: Computes outdoor Wet-Bulb Globe Temperature using the Australian BOM regression with vapor pressure $e$ (Magnus-Tetens) and convective evaporative cooling damping deduction of $0.05^\circ\text{C}$ per m/s above $2.0\,\text{m/s}$ (capped at $-2.0^\circ\text{C}$).

#### `get_risk_category(wbgt_c: float) -> Dict[str, Any]`
- **Parameters**: `wbgt_c` (`float`) — WBGT in °C.
- **Return Type**: `Dict[str, Any]` with keys `"category"`, `"level"`, `"color"`, `"weight"`, `"description"`.
- **Purpose**: Maps WBGT to international occupational heat risk tiers: Low (<28°C), Caution (28–30°C), Danger (30–32°C), Extreme Danger (32–35°C), Severe (>35°C).

#### `calculate_risk_score(wbgt_c: float, elderly_pct: float, outdoor_worker_pct: float) -> float`
- **Parameters**: `wbgt_c` (`float`), `elderly_pct` (`float`), `outdoor_worker_pct` (`float`).
- **Return Type**: `float`
- **Purpose**: Evaluates demographic vulnerability score: $\text{weight} \times (1 + 0.5 \times \text{elderly}/100 + 0.5 \times \text{outdoor}/100)$.

#### `calculate_heat_stress_score(wbgt_c: float, hi_c: float, rh_pct: float) -> int`
- **Parameters**: `wbgt_c` (`float`), `hi_c` (`float`), `rh_pct` (`float`).
- **Return Type**: `int` (range $0\text{--}100$)
- **Purpose**: Computes the ClimateGuard-derived normalized decision-support indicator:
  - $\text{wbgt\_norm} = \text{clamp}(0, 100, ((WBGT - 22.0) / 15.0) \times 100)$
  - $\text{hi\_norm} = \text{clamp}(0, 100, ((HI - 25.0) / 25.0) \times 100)$
  - $\text{rh\_norm} = \text{clamp}(0, 100, ((RH - 30.0) / 60.0) \times 100)$
  - $\text{score} = \text{round}(0.55 \times \text{wbgt\_norm} + 0.35 \times \text{hi\_norm} + 0.10 \times \text{rh\_norm})$.

#### `get_heat_stress_tier(score: int) -> Dict[str, str]`
- **Parameters**: `score` (`int`, $0\text{--}100$).
- **Return Type**: `Dict[str, str]` with keys `"tier"` and `"color"`.
- **Purpose**: Maps 0–100 score to CRITICAL (>=85), VERY HIGH (>=70), HIGH (>=55), MODERATE (>=40), LOW (<40).

---

### Module: `backend/profiles.py`

#### `get_all_profiles() -> List[Dict[str, Any]]`
- **Return Type**: `List[Dict[str, Any]]`
- **Purpose**: Returns the 9 registered population profiles with baseline exposure and sensitivity factors.

#### `calculate_profile_impact(wbgt: float, temp: float, rh: float, profile_id: str) -> Dict[str, Any]`
- **Parameters**: `wbgt` (`float`), `temp` (`float`), `rh` (`float`), `profile_id` (`str`).
- **Return Type**: `Dict[str, Any]`
- **Purpose**: Computes tailored impact score and detailed 6-point bulletin.

---

### Module: `backend/spatial.py`

#### `interpolate_idw(lat: float, lon: float, stations: List[Dict[str, Any]], power: float = 2.0, smoothing: float = 0.08) -> Dict[str, Any]`
- **Return Type**: `Dict[str, Any]`
- **Purpose**: Evaluates Inverse Distance Weighting interpolation across station coordinates.

#### `generate_spatial_heat_grid(stations: List[Dict[str, Any]], lat_steps: int = 18, lon_steps: int = 18) -> Dict[str, Any]`
- **Return Type**: `Dict[str, Any]`
- **Purpose**: Generates regional continuous thermal grid across South India.

---

### Module: `backend/main.py`

#### `load_districts() -> List[Dict[str, Any]]`
- **Purpose**: Loads authoritative 83 South India district records.
#### `validate_startup_districts()`
- **Purpose**: Startup event asserting exactly 38 TN, 14 KL, and 31 KA districts.
#### `fetch_and_compute_districts(force_refresh: bool = False) -> List[Dict[str, Any]]`
- **Purpose**: Manages 10-minute cache and batched Open-Meteo queries for all 83 districts.
#### `sync_alerts_from_districts(districts: List[Dict[str, Any]]) -> List[Dict[str, Any]]`
- **Purpose**: Generates and updates traceable alert records in `ALERTS_REGISTRY`.
#### `get_districts(refresh: bool = False)`
- **Purpose**: Route handler for `GET /api/districts`.
#### `get_district_forecast(district_id: str)`
- **Purpose**: Route handler for `GET /api/districts/{district_id}/forecast`.
#### `get_district_advisory(district_id: str)`
- **Purpose**: Route handler for `GET /api/districts/{district_id}/advisory`.
#### `get_district_profile_impact(district_id: str, profile_id: str = "general_public")`
- **Purpose**: Route handler for `GET /api/districts/{district_id}/impact`.
#### `get_alerts()`
- **Purpose**: Route handler for `GET /api/alerts`.
#### `acknowledge_alert(alert_id: str)`
- **Purpose**: Route handler for `POST /api/alerts/{alert_id}/acknowledge`.
#### `escalate_alert(alert_id: str)`
- **Purpose**: Route handler for `POST /api/alerts/{alert_id}/escalate`.
#### `send_public_alert(alert_id: str)`
- **Purpose**: Route handler for `POST /api/alerts/{alert_id}/send-public`.
#### `generate_simulated_alert(payload: AlertRequest)`
- **Purpose**: Route handler for `POST /api/alert`.

---

## 6. Every React Component

### 1. `Header` (`frontend/src/components/Header.jsx`)
- **Props**: `currentView` (`string`), `onViewChange` (`function`), `lastUpdated` (`string`).
- **State**: None (controlled presentation).
- **Renders**: Brand header with live pulse dot, timestamp, and navigation view toggles ("Public View" vs. "Admin View").
- **Endpoints Called**: None directly.

---

### 2. `IndiaHeatMap` (`frontend/src/components/IndiaHeatMap.jsx`)
- **Props**: `zones` (`Array` of 83 districts), `selectedZone` (`Object`), `onSelectZone` (`function`), `height` (`string`), `isAdminView` (`boolean`).
- **State**: `districtsGeo` (`Object` | `null`), `statesGeo` (`Object` | `null`), `activeMetric` (`string`), `selectedStateView` (`string`), `currentZoom` (`number`).
- **Renders**:
  - Leaflet `MapContainer` centered on South India ($11.5^\circ\text{N}, 77.5^\circ\text{E}$).
  - **Real Geographic Basemap**: Authentic OpenStreetMap / CartoDB Dark Matter base tile layer (`dark_nolabels`) revealing real roads, waterways, coastlines, and topography.
  - **Semi-Transparent Thermal Overlay**: Authoritative 83-district GeoJSON polygons styled dynamically by WBGT risk category with semi-transparent fill (`fillOpacity: 0.36 - 0.58`) so geographical landmarks and terrain remain visible.
  - **Upper Labels Overlay**: CartoDB Dark Matter labels layer (`dark_only_labels`) rendered in a custom Leaflet `labelsPane` (`zIndex: 450`, `pointerEvents: 'none'`) above the polygons, ensuring crisp city names (Chennai, Bengaluru, Coimbatore, Kochi, etc.), towns, and localities as the user zooms in.
  - Compact district tooltip (Name, State, WBGT, Heat Index, Temp, Humidity, Wind, Risk Category, Heat Stress Tier).
  - Cleaned, un-overlapped legend focused purely on `THERMAL RISK — WBGT` and standard risk categories.
- **Endpoints Called**: None directly (loads `/south_india_districts.geojson` from public assets).

---

### 3. `PublicDashboard` (`frontend/src/components/PublicDashboard.jsx`)
- **Props**: `zones` (`Array`), `selectedZone` (`Object`), `onSelectZone` (`function`), `apiBase` (`string`), `onRefreshTelemetry` (`function`), `refreshing` (`boolean`), `refreshError` (`string` | `null`), `lastUpdated` (`string`).
- **State**: `selectedProfile` (`string`), `impactData` (`Object` | `null`), `impactLoading` (`boolean`), `showHssInfo` (`boolean`).
- **Renders**:
  - **Balanced 50% / 50% Desktop Layout**:
    - **Left Section (50% width)**: Independently scrollable container (`overflow-y: auto`, smooth scrolling) containing:
      - Clean data status indicator (redundant count badge removed).
      - District Selector & Header Card (district name, state, lat/long, category risk badge).
      - Heat Impact Bulletin (population profile selector and substantially expanded scrollable content container `.bulletin-scroll-wrapper` with subtle scrollbar, comfortable line height, and zero text cropping).
      - Conditional Health Action Plan (rendered ONLY when risk is Danger, Extreme Danger, or Severe, tailored to selected profile with dedicated scrollable action list).
      - Balanced Live Thermal Telemetry Card (2x2 grid for Ambient Temp, Humidity, Wind, Heat Index; followed by full-width WBGT and Heat Stress Score cards with non-wrapping, non-cropped values and interactive decision-support info popover).
    - **Right Section (50% width)**: Sticky GIS Heat Map (`IndiaHeatMap`) remaining fixed in place while the user scrolls through left-panel decision-support directives.
- **Endpoints Called**:
  - `GET /api/districts/{selectedZone.id}/impact?profile_id={selectedProfile}`.

---

### 4. `AdminDashboard` (`frontend/src/components/AdminDashboard.jsx`)
- **Props**: `zones` (`Array`), `selectedZone` (`Object`), `onSelectZone` (`function`), `apiBase` (`string`), `onShowToast` (`function`).
- **State**: `forecastData` (`Array`), `forecastLoading` (`boolean`), `alertsList` (`Array`), `alertLogs` (`Array`), `isAlerting` (`boolean`), `selectedState` (`string`), `actions` (`Object`).
- **Renders**:
  - **Left Column (50% width)**: Independently scrollable operational column with high-risk district groupings (Severe, Extreme, Danger), multi-day forecast chart, municipal action checklist, and traceable alert escalation workflow (48-Hour Early Warnings vs Today's Alerts).
  - **Right Column (50% width)**: Sticky GIS Heat Map with prominent high-risk district highlights remaining locked in position during left-column review.
- **Endpoints Called**:
  - `GET /api/alerts`
  - `POST /api/alerts/{id}/acknowledge`
  - `POST /api/alerts/{id}/escalate`
  - `POST /api/alerts/{id}/send-public`
  - `GET /api/districts/{selectedZone.id}/forecast`
  - `POST /api/alert`

---

### 5. `App` (`frontend/src/App.jsx`)
- **Props**: None (Root container).
- **State**: `zones` (`Array`), `selectedZone` (`Object`), `currentView` (`string`), `loading` (`boolean`), `refreshing` (`boolean`), `refreshError` (`string` | `null`), `error` (`string` | `null`), `lastUpdated` (`string`), `toastMessage` (`string` | `null`).
- **Renders**:
  - `Header` navigation bar.
  - Conditional view rendering (`PublicDashboard` or `AdminDashboard`).
  - Global toast notification alert banner.
  - Institutional footer with non-clinical decision-support disclaimers.
- **Endpoints Called**:
  - `GET /api/districts` on initial mount.
  - `GET /api/districts?refresh=true` on manual refresh button trigger.

---

## 7. Every Formula Implemented (Exact Code)

The mathematical thermal algorithms are strictly implemented in `backend/heat_index.py`:

### 1. Temperature Conversions
```python
def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9.0 / 5.0) + 32.0

def fahrenheit_to_celsius(fahrenheit: float) -> float:
    return (fahrenheit - 32.0) * 5.0 / 9.0
```

### 2. NOAA Rothfusz Regression Heat Index (°C)
```python
def calculate_heat_index(temp_c: float, rh: float) -> float:
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
```

### 3. Australian BOM Outdoor WBGT with Evaporative Wind Adjustment (°C)
```python
def calculate_wbgt(temp_c: float, rh: float, wind_speed_mps: float = 0.0) -> float:
    # Water vapor pressure e in hPa (Magnus-Tetens formula)
    e = (rh / 100.0) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    wbgt_raw = 0.567 * temp_c + 0.393 * e + 3.94

    # Evaporative cooling wind adjustment
    # Deducts 0.05°C per m/s of wind speed above 2 m/s, capped at -2.0°C
    wind_damping = 0.0
    if wind_speed_mps > 2.0:
        wind_damping = min(2.0, 0.05 * (wind_speed_mps - 2.0))

    wbgt_final = wbgt_raw - wind_damping
    return round(wbgt_final, 1)
```

### 4. ClimateGuard-Derived Normalized Heat Stress Score (0–100 Scale)
```python
def calculate_heat_stress_score(wbgt_c: float, hi_c: float, rh_pct: float) -> int:
    """
    Normalized 0–100 decision-support score combining:
    - WBGT (55% weight): Primary outdoor occupational thermal stress index
    - Heat Index (35% weight): Apparent metabolic humidity temperature
    - Relative Humidity (10% weight): Evaporative sweat cooling resistance
    """
    wbgt_norm = max(0.0, min(100.0, ((wbgt_c - 22.0) / 15.0) * 100.0))
    hi_norm = max(0.0, min(100.0, ((hi_c - 25.0) / 25.0) * 100.0))
    rh_norm = max(0.0, min(100.0, ((rh_pct - 30.0) / 60.0) * 100.0))

    combined = (0.55 * wbgt_norm) + (0.35 * hi_norm) + (0.10 * rh_norm)
    return int(round(max(0.0, min(100.0, combined))))
```

### 5. Heat Stress Tier Classification
```python
def get_heat_stress_tier(score: int) -> Dict[str, str]:
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
```

### 6. International WBGT Risk Category Classification
```python
def get_risk_category(wbgt_c: float) -> Dict[str, Any]:
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
```

### 7. Rule-Based Demographic Vulnerability Score
```python
def calculate_risk_score(
    wbgt_c: float,
    elderly_pct: float,
    outdoor_worker_pct: float
) -> float:
    cat_info = get_risk_category(wbgt_c)
    weight = cat_info["weight"]
    demographic_multiplier = 1.0 + (0.5 * (elderly_pct / 100.0)) + (0.5 * (outdoor_worker_pct / 100.0))
    score = weight * demographic_multiplier
    return round(score, 2)
```

### 8. Historical Thermal Analogue Similarity Distance & Matching Algorithm
```python
def calculate_analogue_similarity(current: dict, historical: dict) -> float:
    """
    Weighted normalized Euclidean distance across 6-variable thermal signature.
    Converts multi-dimensional thermal distance into a 0-100% similarity score.
    """
    WEIGHTS = {
        "wbgt": 0.30,         # Primary human thermal stress index
        "temp": 0.25,         # Ambient air temperature
        "heat_index": 0.20,   # Apparent humidity-adjusted temp
        "humidity": 0.15,     # Moisture content
        "wind": 0.05,         # Surface wind speed
        "consecutive": 0.05   # Heat duration / consecutive days
    }
    BOUNDS = {
        "wbgt": (20.0, 38.0),
        "temp": (20.0, 45.0),
        "heat_index": (22.0, 50.0),
        "humidity": (20.0, 95.0),
        "wind": (0.0, 15.0),
        "consecutive": (0.0, 10.0)
    }
    
    dist_sq = 0.0
    for k, (min_v, max_v) in BOUNDS.items():
        norm_c = (max(min_v, min(max_v, current[k])) - min_v) / (max_v - min_v)
        norm_h = (max(min_v, min(max_v, historical[k])) - min_v) / (max_v - min_v)
        dist_sq += WEIGHTS[k] * ((norm_c - norm_h) ** 2)
    
    dist = math.sqrt(dist_sq)
    return round(max(0.0, min(100.0, (1.0 - dist) * 100.0)), 1)
```

---

## 8. Environment Variables

All runtime configuration and optional keys reside in `.env` at the project root:

| Variable | Example Value | Description |
| :--- | :--- | :--- |
| `MORTALITY_DATA_FILE` | `mortality_synthetic_daily_gemini.csv` | File name or path of the synthetic daily mortality dataset. To swap to a Claude-generated dataset without rewriting code, set to `mortality_synthetic_daily_claude.csv`. |
| `MORTALITY_DATA_SOURCE` | `synthetic_gemini` | Identifier for the dataset generation source (`synthetic_gemini`, `synthetic_claude`). Configures version metadata automatically. |
| `HF_TOKEN` | `hf_AbCdEf123456...` | Personal Hugging Face access token for LLM advisory synthesis. If left blank or omitted, system falls back to authoritative deterministic templates. |
| `HF_MODEL_ID` | `microsoft/Phi-3-mini-4k-instruct` | Instruct LLM repository ID on Hugging Face. |
| `VITE_API_BASE` | `http://127.0.0.1:8000` | (Frontend) Base URL for backend REST API. |

---

## 9. Fully Functional vs. Stubbed / Simulated Components

| Feature Component | Operational Status | Technical Implementation Details |
| :--- | :--- | :--- |
| **83-District South India Choropleth** | **100% Fully Functional** | All 83 districts (38 TN, 14 KL, 31 KA) rendered with authentic GeoJSON boundaries and dynamic risk-based styling. |
| **Open-Meteo Batched Telemetry** | **100% Fully Functional** | Live queries fetch real-time ambient temp, relative humidity, and wind speed; 10-minute cache TTL. |
| **Synthetic Mortality Provider** | **100% Fully Functional** | Abstract provider (`SyntheticCSVProvider`) with strict schema validation (1,095 records, 365 days x 3 states, 2025 date range). Zero-code dataset swap via `MORTALITY_DATA_FILE`. |
| **Historical Thermal Analogue Engine** | **100% Fully Functional** | Multi-variable weighted normalized Euclidean distance matching top 5 historical synthetic scenarios per district based on parent state. |
| **Public Bulletin Historical Impact** | **100% Fully Functional** | Compact scannable bullet in the Heat Impact Bulletin showing matching scenarios, average simulated rate per 100,000, most affected cohort, and non-forecast disclaimer. |
| **Admin Historical Synthetic Panel** | **100% Fully Functional** | Current vs Historical Analogue comparison, simulated mortality burden (avg, median, min-max), age distribution bars, gender ratio, and transparent provenance badges. |
| **48-Hour Early Warning Analogue Integration** | **100% Fully Functional** | Computes projected thermal conditions for 48h hazard districts and attaches historical synthetic analogue burden to alert cards. |
| **Manual Refresh & Stale Fallback** | **100% Fully Functional** | `[↻]` button updates telemetry on demand without page reload; preserves last known good data if network fails. |
| **Heat Stress Score (0–100)** | **100% Fully Functional** | Deterministic multi-variable algorithm with popover clarifying its non-clinical decision-support role. |
| **Heat Impact Bulletin Scrolling** | **100% Fully Functional** | Isolated `.bulletin-scroll-wrapper` enables smooth vertical scrolling without whole-page scroll or text cropping. |
| **Conditional Health Action Plan** | **100% Fully Functional** | Dynamically appears only when district reaches Danger, Extreme, or Severe; tailored to active profile. |
| **Admin High-Risk Overview** | **100% Fully Functional** | Automatically aggregates and groups districts by SEVERE, EXTREME, and DANGER with click-to-focus map centering. |
| **Alert Escalation Workflow** | **Fully Functional Simulation** | Traceable records with state transitions (`PENDING`, `ACKNOWLEDGED`, `ESCALATED`, `PUBLIC_ALERT_SENT`), labeled with transparent `SIMULATED NOTIFICATION` indicators. |
| **Multi-Day Forecast Chart** | **100% Fully Functional** | Live 7-day Chart.js forecast curves for WBGT, HI, and Max Temp. |

---

## 10. Steps to Run the Project Locally from a Clean Clone

### Prerequisites
- Python `3.11+`
- Node.js `v18+` or `v20+` (tested on `v24.13.0`)
- Git

### Step 1: Clone Repository
```bash
git clone <repo-url> climateguard-india
cd climateguard-india
```

### Step 2: Configure Environment Variables
Create `.env` in the project root:
```env
HF_TOKEN=
HF_MODEL_ID=microsoft/Phi-3-mini-4k-instruct
```

### Step 3: Setup and Launch Backend
```bash
# 1. Install dependencies
pip install fastapi uvicorn httpx pydantic python-dotenv pytest

# 2. Run test suites
py -m pytest backend/test_heat_index.py -v
py backend/test_api_endpoints.py

# 3. Start backend server
cd backend
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
API docs available at `http://127.0.0.1:8000/docs`.

### Step 4: Setup and Launch Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### Step 5: Access Dashboards
- **Public Dashboard**: Open `http://127.0.0.1:5173/` in a browser.
- **Admin Command Dashboard**: Open `http://127.0.0.1:5173/admin` or click "Admin View".

---

## 11. Known Limitations & Intentional Out-of-Scope Decisions

1. **Simulated Telephony Integration**:
   - *Rationale*: Paid SMS gateway or WhatsApp Business API setups require commercial verification and billing. The system provides a complete dispatch simulation with audit logging in `alerts.log` and explicit `SIMULATED NOTIFICATION` badges.
2. **Deterministic Decision-Support Indicators**:
   - *Rationale*: Heat Stress Score ($0\text{--}100$) and demographic vulnerability index are computational decision-support tools, not clinical diagnoses or epidemiological mortality forecasts.
3. **In-Memory Caching (No SQL Database)**:
   - *Rationale*: Eliminates external database dependencies while providing sub-millisecond retrieval and automated 10-minute cache invalidation.
4. **Geographic Focus on South India**:
   - *Rationale*: Restricting coverage to Tamil Nadu (38), Kerala (14), and Karnataka (31) guarantees high boundary precision, zero boundary clipping, and verified interior coordinates across all 83 districts.
