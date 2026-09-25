"""
ClimateGuard India - Spatial Thermal Risk Interpolation Engine
Generates continuous spatial thermal surfaces from live meteorological station telemetry
using Inverse Distance Weighting (IDW) interpolation.
"""

import math
from typing import List, Dict, Any

from heat_index import (
    calculate_heat_index,
    calculate_wbgt,
    get_risk_category,
)


def interpolate_idw(
    lat: float,
    lon: float,
    stations: List[Dict[str, Any]],
    power: float = 2.0,
    smoothing: float = 0.08
) -> Dict[str, Any]:
    """
    Computes spatially interpolated meteorological telemetry at (lat, lon)
    using Inverse Distance Weighting (IDW) against live station observations.
    Then evaluates exact thermal stress algorithms (Rothfusz HI & BOM WBGT).
    """
    total_weight = 0.0
    weighted_temp = 0.0
    weighted_rh = 0.0
    weighted_wind = 0.0
    weighted_solar = 0.0

    for s in stations:
        d_lat = lat - s["lat"]
        d_lon = lon - s["lon"]
        # Approximate euclidean distance in degrees (sufficient for regional interpolation)
        dist = math.sqrt(d_lat * d_lat + d_lon * d_lon)
        
        weight = 1.0 / math.pow(dist + smoothing, power)
        total_weight += weight
        
        weighted_temp += weight * s["temp"]
        weighted_rh += weight * s["rh"]
        weighted_wind += weight * s["wind"]
        weighted_solar += weight * float(s.get("solar_radiation", s.get("solar", 0.0)))

    if total_weight == 0.0:
        total_weight = 1.0

    interp_temp = round(weighted_temp / total_weight, 1)
    interp_rh = round(weighted_rh / total_weight, 1)
    interp_wind = round(weighted_wind / total_weight, 1)
    interp_solar = round(weighted_solar / total_weight, 1)

    # Compute exact formulas on interpolated values
    hi = calculate_heat_index(interp_temp, interp_rh)
    wbgt = calculate_wbgt(interp_temp, interp_rh, interp_wind, interp_solar)
    cat_info = get_risk_category(wbgt)

    return {
        "lat": round(lat, 2),
        "lon": round(lon, 2),
        "temp": interp_temp,
        "rh": interp_rh,
        "wind": interp_wind,
        "hi": hi,
        "wbgt": wbgt,
        "category": cat_info["category"],
        "level": cat_info["level"],
        "color": cat_info["color"],
        "weight": cat_info["weight"]
    }


def generate_spatial_heat_grid(
    stations: List[Dict[str, Any]],
    lat_steps: int = 18,
    lon_steps: int = 18
) -> Dict[str, Any]:
    """
    Constructs a regional spatial grid over the Indian subcontinent
    (Lat: 8.0°N to 36.0°N, Lon: 68.0°E to 96.0°E) evaluating continuous
    thermal metrics across the landmass.
    """
    min_lat, max_lat = 8.0, 36.0
    min_lon, max_lon = 68.0, 96.0

    lat_step = (max_lat - min_lat) / (lat_steps - 1)
    lon_step = (max_lon - min_lon) / (lon_steps - 1)

    points = []
    for i in range(lat_steps):
        lat = min_lat + i * lat_step
        for j in range(lon_steps):
            lon = min_lon + j * lon_step
            # Perform IDW interpolation from real station data
            val = interpolate_idw(lat, lon, stations)
            points.append(val)

    return {
        "bounds": {
            "southWest": [min_lat, min_lon],
            "northEast": [max_lat, max_lon]
        },
        "resolution": {
            "lat_steps": lat_steps,
            "lon_steps": lon_steps
        },
        "points_count": len(points),
        "points": points,
        "stations_count": len(stations),
        "model_notice": "Interpolated spatial thermal surface derived from live Open-Meteo station telemetry using Inverse Distance Weighting (IDW). Illustrative early-warning visual."
    }
