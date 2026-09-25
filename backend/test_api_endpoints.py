"""
Comprehensive test script for ClimateGuard India backend endpoints (South India 83-District Scope).
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_tests():
    print(">>> 1. Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health_data = r.json()
    print("Health response:", health_data)
    assert health_data["total_districts"] == 83
    assert health_data["states"]["Tamil Nadu"] == 38
    assert health_data["states"]["Kerala"] == 14
    assert health_data["states"]["Karnataka"] == 31

    print("\n>>> 2. Testing /api/districts (83 districts, batched Open-Meteo & formula integration)...")
    r = client.get("/api/districts")
    assert r.status_code == 200, f"Districts failed: {r.text}"
    data = r.json()
    assert data["total"] == 83
    assert len(data["districts"]) == 83
    assert data["states"]["Tamil Nadu"] == 38
    assert data["states"]["Kerala"] == 14
    assert data["states"]["Karnataka"] == 31
    
    first_d = data["districts"][0]
    print(f"Loaded {data['total']} districts. Sample: {first_d['name']} ({first_d['state']}): Temp={first_d['temp']}°C, WBGT={first_d['wbgt']}°C, HI={first_d['hi']}°C, Category={first_d['category']}, Risk Score={first_d['risk_score']}")
    
    # Check that cache works on 2nd call
    r2 = client.get("/api/districts")
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    print("Cache hit confirmed on subsequent call!")

    print("\n>>> 3. Testing backward-compatible alias /api/zones...")
    r_zones = client.get("/api/zones")
    assert r_zones.status_code == 200
    assert len(r_zones.json()["zones"]) == 83

    print("\n>>> 4. Testing /api/districts/chennai/forecast...")
    r = client.get("/api/districts/chennai/forecast")
    assert r.status_code == 200, f"Forecast failed: {r.text}"
    f_data = r.json()
    assert "forecast" in f_data and len(f_data["forecast"]) > 0
    print(f"Forecast for {f_data['name']} ({f_data['state']}): {len(f_data['forecast'])} days retrieved.")
    sample_day = f_data["forecast"][0]
    print(f"Sample forecast day {sample_day['date']}: Max Temp={sample_day['temp_max']}°C, WBGT={sample_day['wbgt']}°C, HI={sample_day['hi']}°C, Category={sample_day['category']}")

    print("\n>>> 5. Testing /api/districts/bengaluru_urban/forecast...")
    r_blr = client.get("/api/districts/bengaluru_urban/forecast")
    assert r_blr.status_code == 200
    print(f"Bengaluru Urban forecast retrieved: {len(r_blr.json()['forecast'])} days.")

    print("\n>>> 6. Testing /api/districts/chennai/advisory (HF + 3s timeout + graceful fallback)...")
    r = client.get("/api/districts/chennai/advisory")
    assert r.status_code == 200, f"Advisory failed: {r.text}"
    adv_data = r.json()
    assert "advisory" in adv_data
    print(f"Advisory for {adv_data['district_name']} (source: {adv_data.get('source')}): {adv_data['advisory']}")

    print("\n>>> 7. Testing POST /api/alert (Telegram multilingual alert broadcast)...")
    r = client.post("/api/alert", json={"district_id": "chennai"})
    assert r.status_code == 200, f"Alert failed: {r.text}"
    alert_data = r.json()
    assert alert_data["channel"] == "Telegram"
    assert "sent" in alert_data
    assert "languages" in alert_data
    print(f"Telegram alert processed for {alert_data['district_name']} ({alert_data['state']}) - Sent: {alert_data['sent']}:")
    print(alert_data["message"])

    print("\n>>> 8. Testing /api/profiles...")
    r = client.get("/api/profiles")
    assert r.status_code == 200, f"Profiles failed: {r.text}"
    p_data = r.json()
    assert isinstance(p_data, list) and len(p_data) >= 9
    print(f"Retrieved {len(p_data)} population profiles.")

    print("\n>>> 9. Testing /api/districts/chennai/impact (Profile impact: IT vs Construction)...")
    r_it = client.get("/api/districts/chennai/impact?profile_id=it_office")
    assert r_it.status_code == 200, f"IT impact failed: {r_it.text}"
    it_impact = r_it.json()["impact"]

    r_const = client.get("/api/districts/chennai/impact?profile_id=construction_labor")
    assert r_const.status_code == 200, f"Construction impact failed: {r_const.text}"
    const_impact = r_const.json()["impact"]

    print(f"Chennai IT Worker -> Score: {it_impact['profile_score']}, Level: {it_impact['impact_level']}, Exposure: {it_impact['bulletin']['exposure']}")
    print(f"Chennai Construction Worker -> Score: {const_impact['profile_score']}, Level: {const_impact['impact_level']}, Exposure: {const_impact['bulletin']['exposure']}")
    assert it_impact["profile_score"] < const_impact["profile_score"], "Construction worker should have higher thermal vulnerability than IT worker!"

    print("\n>>> 10. Testing /api/districts?refresh=true & Heat Stress Score (0-100)...")
    r_refresh = client.get("/api/districts?refresh=true")
    assert r_refresh.status_code == 200, f"Refresh failed: {r_refresh.text}"
    ref_data = r_refresh.json()
    assert ref_data["total"] == 83
    first_district = ref_data["districts"][0]
    assert "heat_stress_score" in first_district, "Missing heat_stress_score in district record"
    assert 0 <= first_district["heat_stress_score"] <= 100, f"Heat stress score {first_district['heat_stress_score']} out of range 0-100"
    print(f"Manual refresh confirmed! District {first_district['name']} -> Heat Stress Score: {first_district['heat_stress_score']}/100, Tier: {first_district.get('heat_stress_tier')}")

    print("\n>>> 11. Testing /api/alerts (48-Hour Early Warnings & Today's Alerts)...")
    r_alerts = client.get("/api/alerts")
    assert r_alerts.status_code == 200, f"Alerts fetch failed: {r_alerts.text}"
    alerts_payload = r_alerts.json()
    assert "alerts" in alerts_payload and len(alerts_payload["alerts"]) > 0
    print(f"Retrieved {len(alerts_payload['alerts'])} active alerts. Summary: {alerts_payload['summary']}")
    sample_alert = alerts_payload["alerts"][0]
    sample_alert_id = sample_alert["alert_id"]
    print(f"Sample alert: {sample_alert_id} for {sample_alert['district_name']} ({sample_alert['trigger_type']}) - Status: {sample_alert['status']}")

    print(f"\n>>> 12. Testing alert workflow actions on {sample_alert_id}...")
    # Acknowledge
    r_ack = client.post(f"/api/alerts/{sample_alert_id}/acknowledge")
    assert r_ack.status_code == 200
    ack_res = r_ack.json()["alert"]
    assert ack_res["status"] == "ACKNOWLEDGED"
    assert ack_res["acknowledged_by"] is not None
    print(f"Alert acknowledged by: {ack_res['acknowledged_by']} at {ack_res['acknowledged_at']}")

    # Escalate
    r_esc = client.post(f"/api/alerts/{sample_alert_id}/escalate")
    assert r_esc.status_code == 200
    esc_res = r_esc.json()["alert"]
    assert esc_res["status"] == "ESCALATED"
    assert esc_res["escalated_to"] is not None
    print(f"Alert escalated to: {esc_res['escalated_to']}")

    # Send Public Alert
    r_pub = client.post(f"/api/alerts/{sample_alert_id}/send-public")
    assert r_pub.status_code == 200
    pub_res = r_pub.json()["alert"]
    assert pub_res["status"] == "PUBLIC_ALERT_SENT"
    print(f"Public alert dispatched: {pub_res['public_alert_status']}")

    print("\nALL 13 ENDPOINT & WORKFLOW TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    run_tests()

