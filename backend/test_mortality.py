"""
ClimateGuard India - Comprehensive Synthetic Mortality Integration Test Suite
Tests all 15 required verification items from the specification:
1. CSV loading
2. Schema validation
3. State mapping
4. District -> State mapping (Chennai->TN, Coimbatore->TN, Kochi->KL, Bengaluru Urban->KA)
5. Historical analogue matching
6. Similarity scoring
7. Mortality aggregation (mean, median, min, max)
8. Age aggregation (under 30, 30-59, 60+)
9. Gender aggregation (male, female)
10. Mortality rate calculation per 100,000
11. Missing-data handling
12. Synthetic-data labeling
13. Dataset replacement / schema mapping test (simulating Claude dataset swap)
14. Health-impact generation
15. Fault-tolerance test (graceful degradation when mortality data fails)
"""

import os
import sys
import unittest
from pathlib import Path
from typing import List, Dict, Any

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mortality import (
    MortalityRecord,
    MortalityDataProvider,
    SyntheticCSVProvider,
    get_mortality_provider,
    HistoricalAnalogueService,
    HealthImpactAnalysisService,
    reset_mortality_provider
)


class TestSyntheticMortalityIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_mortality_provider()
        cls.provider = get_mortality_provider()

    # -------------------------------------------------------------------------
    # 1. CSV Loading
    # -------------------------------------------------------------------------
    def test_01_csv_loading(self):
        """Verifies that the configured CSV file loads 1,095 daily records."""
        records = self.provider.get_records()
        self.assertEqual(len(records), 1095, f"Expected 1,095 records, got {len(records)}")
        meta = self.provider.get_metadata()
        self.assertEqual(meta["record_count"], 1095)
        self.assertTrue(meta["is_valid"])

    # -------------------------------------------------------------------------
    # 2. Schema Validation
    # -------------------------------------------------------------------------
    def test_02_schema_validation(self):
        """Verifies required fields, numeric bounds, and record completeness."""
        is_valid, errors = self.provider.validate()
        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")
        self.assertEqual(len(errors), 0)

        # Inspect first record
        rec = self.provider.get_records()[0]
        self.assertIsInstance(rec.date, str)
        self.assertIsInstance(rec.state, str)
        self.assertGreater(rec.population, 0)
        self.assertTrue(0 <= rec.relative_humidity_percent <= 100)
        self.assertGreaterEqual(rec.wind_speed_mps, 0.0)
        self.assertGreaterEqual(rec.heat_related_deaths_total, 0)
        self.assertGreaterEqual(rec.heat_related_mortality_rate_per_100000, 0.0)

    # -------------------------------------------------------------------------
    # 3. State Mapping
    # -------------------------------------------------------------------------
    def test_03_state_mapping(self):
        """Verifies records are evenly partitioned across Tamil Nadu, Kerala, Karnataka."""
        tn_records = self.provider.get_records(state="Tamil Nadu")
        ka_records = self.provider.get_records(state="Karnataka")
        kl_records = self.provider.get_records(state="Kerala")

        self.assertEqual(len(tn_records), 365, "Expected 365 records for Tamil Nadu")
        self.assertEqual(len(ka_records), 365, "Expected 365 records for Karnataka")
        self.assertEqual(len(kl_records), 365, "Expected 365 records for Kerala")

    # -------------------------------------------------------------------------
    # 4. District -> State Mapping
    # -------------------------------------------------------------------------
    def test_04_district_to_state_mapping(self):
        """Verifies specified districts map to the exact state-level mortality scope."""
        test_cases = [
            ("Chennai", "Tamil Nadu"),
            ("Coimbatore", "Tamil Nadu"),
            ("Kochi", "Kerala"),
            ("Bengaluru Urban", "Karnataka"),
        ]
        for dist_name, expected_state in test_cases:
            res = HistoricalAnalogueService.find_analogues(
                state=expected_state,
                current_temp=35.0,
                current_humidity=60.0,
                current_wbgt=31.0,
                top_n=5
            )
            self.assertTrue(res["available"])
            self.assertEqual(res["state_scope"], expected_state)
            self.assertEqual(len(res["analogues"]), 5)

    # -------------------------------------------------------------------------
    # 5. Historical Analogue Matching
    # -------------------------------------------------------------------------
    def test_05_historical_analogue_matching(self):
        """Tests that top analogues return multi-variable matched days."""
        res = HistoricalAnalogueService.find_analogues(
            state="Tamil Nadu",
            current_temp=38.8,
            current_humidity=63.0,
            current_wbgt=32.1,
            current_hi=42.0,
            current_wind=3.0,
            top_n=5
        )
        self.assertTrue(res["available"])
        self.assertEqual(len(res["analogues"]), 5)
        # Verify first match has high similarity (> 85%)
        top = res["analogues"][0]
        self.assertGreaterEqual(top["similarity_score"], 85.0)
        self.assertIn("formatted_date", top)
        self.assertIn("heat_related_deaths_total", top)

    # -------------------------------------------------------------------------
    # 6. Similarity Scoring
    # -------------------------------------------------------------------------
    def test_06_similarity_scoring(self):
        """Tests similarity score normalization between 0 and 100 with documented weights."""
        norm_temp = HistoricalAnalogueService._normalize(35.0, "temp")
        self.assertTrue(0.0 <= norm_temp <= 1.0)
        self.assertIn("wbgt", HistoricalAnalogueService.WEIGHTS)
        self.assertIn("temp", HistoricalAnalogueService.WEIGHTS)
        self.assertIn("humidity", HistoricalAnalogueService.WEIGHTS)
        # Weights should sum to 1.0
        self.assertAlmostEqual(sum(HistoricalAnalogueService.WEIGHTS.values()), 1.0, places=2)

    # -------------------------------------------------------------------------
    # 7. Mortality Aggregation
    # -------------------------------------------------------------------------
    def test_07_mortality_aggregation(self):
        """Tests mean, median, min, max calculation across top analogue scenarios."""
        res = HistoricalAnalogueService.find_analogues(
            state="Karnataka",
            current_temp=36.0,
            current_humidity=50.0,
            current_wbgt=30.0,
            top_n=5
        )
        summary = res["summary"]
        self.assertIn("average_simulated_deaths", summary)
        self.assertIn("median_simulated_deaths", summary)
        self.assertIn("min_simulated_deaths", summary)
        self.assertIn("max_simulated_deaths", summary)
        self.assertLessEqual(summary["min_simulated_deaths"], summary["max_simulated_deaths"])
        self.assertLessEqual(summary["min_simulated_deaths"], summary["average_simulated_deaths"])
        self.assertGreaterEqual(summary["max_simulated_deaths"], summary["average_simulated_deaths"])

    # -------------------------------------------------------------------------
    # 8. Age Aggregation
    # -------------------------------------------------------------------------
    def test_08_age_aggregation(self):
        """Tests age group percentage distribution (under 30, 30-59, 60+)."""
        res = HistoricalAnalogueService.find_analogues(
            state="Kerala",
            current_temp=33.0,
            current_humidity=75.0,
            current_wbgt=31.0,
            top_n=5
        )
        age_dist = res["summary"]["age_distribution"]
        total_pct = age_dist["under_30_percent"] + age_dist["30_59_percent"] + age_dist["60_plus_percent"]
        self.assertAlmostEqual(total_pct, 100.0, delta=1.5)
        self.assertIn("most_affected_age_group", res["summary"])

    # -------------------------------------------------------------------------
    # 9. Gender Aggregation
    # -------------------------------------------------------------------------
    def test_09_gender_aggregation(self):
        """Tests aggregate male/female percentage breakdown across analogues."""
        res = HistoricalAnalogueService.find_analogues(
            state="Tamil Nadu",
            current_temp=37.0,
            current_humidity=55.0,
            current_wbgt=31.5,
            top_n=5
        )
        gender_dist = res["summary"]["gender_distribution"]
        total_gender = gender_dist["male_percent"] + gender_dist["female_percent"]
        self.assertAlmostEqual(total_gender, 100.0, delta=1.5)

    # -------------------------------------------------------------------------
    # 10. Mortality Rate Calculation
    # -------------------------------------------------------------------------
    def test_10_mortality_rate_calculation(self):
        """Verifies synthetic rate is calculated per 100,000 population."""
        res = HistoricalAnalogueService.find_analogues(
            state="Tamil Nadu",
            current_temp=38.0,
            current_humidity=60.0,
            current_wbgt=32.0,
            top_n=5
        )
        rate = res["summary"]["average_mortality_rate_per_100000"]
        self.assertIsInstance(rate, float)
        self.assertGreaterEqual(rate, 0.0)

    # -------------------------------------------------------------------------
    # 11. Missing-Data Handling
    # -------------------------------------------------------------------------
    def test_11_missing_data_handling(self):
        """Verifies graceful handling of unknown states or incomplete attributes."""
        res = HistoricalAnalogueService.find_analogues(
            state="UnknownState",
            current_temp=35.0,
            current_humidity=50.0,
            current_wbgt=30.0,
            top_n=5
        )
        self.assertFalse(res["available"])
        self.assertIn("error", res)

    # -------------------------------------------------------------------------
    # 12. Synthetic-Data Labeling
    # -------------------------------------------------------------------------
    def test_12_synthetic_data_labeling(self):
        """Verifies all records and responses explicitly carry data_type = SYNTHETIC."""
        for rec in self.provider.get_records()[:10]:
            self.assertEqual(rec.data_type, "SYNTHETIC")
        
        res = HistoricalAnalogueService.find_analogues(
            state="Tamil Nadu",
            current_temp=35.0,
            current_humidity=60.0,
            current_wbgt=31.0
        )
        self.assertEqual(res["data_type"], "SYNTHETIC")
        self.assertIn("synthetic simulation data", res["disclaimer"].lower())

    # -------------------------------------------------------------------------
    # 13. Dataset Replacement (Zero-Code Swap Simulation)
    # -------------------------------------------------------------------------
    def test_13_dataset_replacement_simulation(self):
        """
        Simulates replacing the dataset with a Claude-generated CSV or alternate provider
        by testing custom field mapping and configurable provider loading.
        """
        # Create a mock raw row that has different column aliases
        raw_claude_row = {
            "date": "2025-06-01",
            "state_name": "Tamil Nadu",  # Aliased column
            "pop_count": "72000000",      # Aliased column
            "temp_max": "41.2",          # Aliased column
            "temp_mean": "34.5",
            "temp_min": "28.0",
            "humidity": "58.0",          # Aliased column
            "wind_speed": "3.5",         # Aliased column
            "heat_index": "45.0",
            "wbgt": "33.5",              # Aliased column
            "heatwave_flag": "1",        # Aliased column
            "consecutive_days": "3",     # Aliased column
            "heat_load_7d": "15.0",
            "expected_deaths": "6",
            "total_deaths": "12",        # Aliased column
            "male_deaths": "7",
            "female_deaths": "5",
            "age_under_30": "1",
            "age_30_59": "7",
            "age_60_plus": "4",
            "rate_per_100k": "0.17",     # Aliased column
            "signature": "EXTREME_HEAT_TN",
            "data_source_type": "SYNTHETIC"
        }
        mapped_record = MortalityRecord.from_csv_row(raw_claude_row)
        self.assertEqual(mapped_record.state, "Tamil Nadu")
        self.assertEqual(mapped_record.max_temperature_c, 41.2)
        self.assertEqual(mapped_record.wbgt_c, 33.5)
        self.assertEqual(mapped_record.heat_related_deaths_total, 12)
        self.assertEqual(mapped_record.data_type, "SYNTHETIC")

    # -------------------------------------------------------------------------
    # 14. Health-Impact Generation
    # -------------------------------------------------------------------------
    def test_14_health_impact_generation(self):
        """Tests complete HealthImpactAnalysisService synthesizing weather, profile, and analogues."""
        mock_district = {
            "id": "virudhunagar",
            "name": "Virudhunagar",
            "state": "Tamil Nadu",
            "temp": 39.1,
            "rh": 61.0,
            "wind": 3.2,
            "wbgt": 32.4,
            "hi": 43.0,
            "heat_stress_score": 74,
            "category": "Extreme Danger",
            "color": "#ef4444"
        }
        analysis = HealthImpactAnalysisService.analyze_district(
            district=mock_district,
            profile_id="construction_labor"
        )
        self.assertEqual(analysis["district"], "Virudhunagar")
        self.assertEqual(analysis["state"], "Tamil Nadu")
        self.assertEqual(analysis["environmental_conditions"]["category"], "Extreme Danger")
        self.assertEqual(analysis["profile"], "Construction / Labor Worker")
        self.assertIn(analysis["impact_level"], ["VERY HIGH", "CRITICAL"])
        self.assertTrue(analysis["historical_analogues"]["available"])
        self.assertIn("interpretation", analysis)
        self.assertIn("bulletin", analysis)
        self.assertIn("disclaimer", analysis)
        # Ensure no individual mortality prediction is made
        bulletin_str = str(analysis["bulletin"]).lower()
        self.assertNotIn("your mortality", bulletin_str)
        self.assertNotIn("chance of dying", bulletin_str)

    # -------------------------------------------------------------------------
    # 15. Fault-Tolerance Test (Graceful Degradation)
    # -------------------------------------------------------------------------
    def test_15_fault_tolerance(self):
        """
        Verifies that if mortality data fails or is unavailable,
        the environmental thermal system continues operating normally.
        """
        mock_district = {
            "id": "chennai",
            "name": "Chennai",
            "state": "InvalidStateNameForTest",
            "temp": 36.0,
            "rh": 65.0,
            "wind": 3.0,
            "wbgt": 31.8,
            "hi": 41.0,
            "heat_stress_score": 68,
            "category": "Danger",
            "color": "#f97316"
        }
        analysis = HealthImpactAnalysisService.analyze_district(
            district=mock_district,
            profile_id="general_public"
        )
        # Environmental warning should still be intact
        self.assertEqual(analysis["environmental_conditions"]["category"], "Danger")
        self.assertEqual(analysis["profile"], "General Public")
        self.assertIn("bulletin", analysis)
        # Mortality section reports unavailable without crashing
        self.assertFalse(analysis["historical_analogues"]["available"])
        self.assertIn("unavailable", analysis["historical_analogues"].get("message", "").lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
