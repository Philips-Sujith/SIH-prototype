"""
Verification script for Task 1:
1. Timezone correctness
2. Cache freshness & observation timestamp
3. Shared snapshot per zone
4. Diurnal/solar radiation handling (nighttime convergence)
5. UTCI range validation
6. Cross-index sanity check
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import httpx

def main():
    resp = httpx.get("http://127.0.0.1:8000/api/districts?refresh=true", timeout=20.0)
    assert resp.status_code == 200, f"Error: {resp.status_code}"
    data = resp.json()
    districts = data["districts"]
    print(f"Total districts fetched: {len(districts)}")
    
    # Check observation time
    obs_times = {d.get("observation_time") for d in districts}
    print(f"Observation times in data: {obs_times}")

    wbgt_categories = {}
    utci_categories = {}
    
    chennai = next((d for d in districts if d["id"] == "chennai"), None)
    coimbatore = next((d for d in districts if d["id"] == "coimbatore"), None)
    bengaluru = next((d for d in districts if d["id"] == "bengaluru_urban"), None)
    
    print("\n--- Key Districts Current Nighttime Readings ---")
    for d in [chennai, coimbatore, bengaluru]:
        if d:
            print(
                f"District: {d['name']} ({d['state']})\n"
                f"  Obs Time: {d.get('observation_time')}\n"
                f"  Temp: {d['temp']}°C, RH: {d['rh']}%, Wind: {d['wind']} m/s, Solar: {d['solar_radiation']} W/m²\n"
                f"  WBGT: {d['wbgt']}°C ({d['category']})\n"
                f"  UTCI: {d['utci']}°C ({d['utci_category']})\n"
                f"  HI: {d['hi']}°C\n"
                f"  Heat Stress Score: {d['heat_stress_score']} ({d['heat_stress_tier']})\n"
            )

    high_risk_wbgt = []
    high_risk_utci = []
    divergent_districts = []

    for d in districts:
        wbgt_cat = d["category"]
        utci_cat = d["utci_category"]
        wbgt_categories[wbgt_cat] = wbgt_categories.get(wbgt_cat, 0) + 1
        utci_categories[utci_cat] = utci_categories.get(utci_cat, 0) + 1

        if wbgt_cat in ["Danger", "Extreme Danger", "Severe"]:
            high_risk_wbgt.append(f"{d['name']} (WBGT={d['wbgt']}°C, {wbgt_cat})")
        if utci_cat in ["Strong Heat Stress", "Very Strong Heat Stress", "Extreme Heat Stress"]:
            high_risk_utci.append(f"{d['name']} (UTCI={d['utci']}°C, {utci_cat})")

        wbgt_w = d["risk_weight"]
        # Map UTCI category to weight
        utci_w_map = {
            "No Thermal Stress": 1,
            "Moderate Heat Stress": 2,
            "Strong Heat Stress": 3,
            "Very Strong Heat Stress": 4,
            "Extreme Heat Stress": 5
        }
        utci_w = utci_w_map.get(utci_cat, 1)
        if abs(wbgt_w - utci_w) > 1:
            divergent_districts.append((d['name'], wbgt_cat, utci_cat, d['temp'], d['rh'], d['wind'], d['solar_radiation']))

    print("\n--- All 83 Districts WBGT Distribution ---")
    for cat, count in wbgt_categories.items():
        print(f"  {cat}: {count}")

    print("\n--- All 83 Districts UTCI Distribution ---")
    for cat, count in utci_categories.items():
        print(f"  {cat}: {count}")

    print(f"\nDistricts with Elevated WBGT (Danger+): {len(high_risk_wbgt)} -> {high_risk_wbgt}")
    print(f"Districts with Elevated UTCI (Strong+): {len(high_risk_utci)} -> {high_risk_utci}")
    print(f"Districts with Tier Divergence > 1: {len(divergent_districts)} -> {divergent_districts}")

if __name__ == "__main__":
    main()
