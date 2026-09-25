"""
ClimateGuard India - Synthetic Mortality Data Provider & Historical Analogue Engine
Integrates the Claude synthetic daily heat-related mortality dataset (1,095 records, 61 columns, 2025-2026 TN/KL/KA)
for research prototype demonstration and historical thermal analogue decision-support.

SCIENTIFIC & ARCHITECTURAL PRINCIPLES:
1. Purely Synthetic: Explicitly designated as synthetic research/simulation data.
   Never labeled as official government records (NCRB/IMD), verified deaths, or causal clinical observations.
2. Decision-Support, NOT Forecasting: The system is heat-health decision support.
   Never predicts personal mortality, individual risk probability, or "X people will die".
3. State-Level to District Mapping: Mortality data is state-level; live telemetry is district-level.
   This geographic distinction is explicitly preserved in schema and interpretations.
4. Provider Abstraction: Decoupled via MortalityDataProvider allowing seamless swapping to future datasets
   via configuration without frontend or API changes.
5. 61-Column Schema Preservation: Preserves all rich attributes (demographics, thermal indices, lagged exposure,
   vulnerability, age & gender breakdowns) in a standardized internal representation.
"""

import os
import csv
import math
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from profiles import calculate_profile_impact

logger = logging.getLogger("climateguard.mortality")

# Base directory for mortality datasets
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MORTALITY_DIR = BASE_DIR / "data" / "mortality"
DEFAULT_CSV_FILENAME = "mortality_synthetic_daily.csv"


class MortalityRecord:
    """
    Standardized internal schema for daily mortality observations/simulations.
    Normalizes the 61-column Claude synthetic schema and preserves all fields,
    while maintaining backward-compatible property accessors.
    """
    @classmethod
    def from_csv_row(cls, row: Dict[str, Any]) -> "MortalityRecord":
        """Factory method to construct a validated MortalityRecord from raw row with aliases."""
        alias_map = {
            "state_name": "state",
            "pop_count": "population",
            "temp_max": "maximum_temperature_c",
            "max_temp": "maximum_temperature_c",
            "max_temperature_c": "maximum_temperature_c",
            "temp_mean": "mean_temperature_c",
            "mean_temp": "mean_temperature_c",
            "temp_min": "minimum_temperature_c",
            "min_temp": "minimum_temperature_c",
            "min_temperature_c": "minimum_temperature_c",
            "humidity": "relative_humidity_percent",
            "relative_humidity": "relative_humidity_percent",
            "wind": "wind_speed_mps",
            "wind_speed": "wind_speed_mps",
            "heat_index": "heat_index_c",
            "wbgt": "wbgt_c",
            "heatwave_flag": "heatwave_day",
            "consecutive_days": "consecutive_heat_days",
            "consecutive_hot_days": "consecutive_heat_days",
            "heat_load_7d": "cumulative_heat_load_7day",
            "total_deaths": "heat_related_deaths_total",
            "deaths_total": "heat_related_deaths_total",
            "male_deaths": "heat_related_deaths_male",
            "female_deaths": "heat_related_deaths_female",
            "deaths_male": "heat_related_deaths_male",
            "deaths_female": "heat_related_deaths_female",
            "age_under_30": "heat_related_deaths_under_30",
            "deaths_under_30": "heat_related_deaths_under_30",
            "age_30_59": "heat_related_deaths_30_59",
            "deaths_30_59": "heat_related_deaths_30_59",
            "age_60_plus": "heat_related_deaths_60_plus",
            "deaths_60_plus": "heat_related_deaths_60_plus",
            "rate_per_100k": "heat_related_mortality_rate_per_100000",
            "mortality_rate": "heat_related_mortality_rate_per_100000",
            "signature": "thermal_signature",
            "data_source_type": "data_type"
        }
        norm = {}
        for k, v in row.items():
            clean_k = k.strip().lower()
            target_k = alias_map.get(clean_k, clean_k)
            norm[target_k] = v
        return cls(norm)

    def __init__(self, raw_data: Dict[str, Any]):
        def _float(key: str, default: float = 0.0) -> float:
            val = raw_data.get(key)
            if val is None or val == "":
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def _int(key: str, default: int = 0) -> int:
            val = raw_data.get(key)
            if val is None or val == "":
                return default
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default

        def _bool(key: str, default: bool = False) -> bool:
            val = raw_data.get(key)
            if val is None or val == "":
                return default
            val_str = str(val).strip().lower()
            return val_str in ["true", "1", "yes"]

        # Core Metadata
        self.date: str = str(raw_data.get("date", "")).strip()
        self.state: str = str(raw_data.get("state", "")).strip()
        self.data_type: str = str(raw_data.get("data_type", "SYNTHETIC")).strip()
        self.population: int = _int("population")

        # Demographics
        self.elderly_population_percent: float = _float("elderly_population_percent")
        self.working_age_population_percent: float = _float("working_age_population_percent")
        self.under_30_population_percent: float = _float("under_30_population_percent")
        self.outdoor_worker_fraction: float = _float("outdoor_worker_fraction")
        self.urban_population_percent: float = _float("urban_population_percent")

        # Weather & Anomalies
        self.maximum_temperature_c: float = _float("maximum_temperature_c") or _float("max_temperature_c")
        self.minimum_temperature_c: float = _float("minimum_temperature_c") or _float("min_temperature_c")
        self.mean_temperature_c: float = _float("mean_temperature_c")
        self.relative_humidity_percent: float = _float("relative_humidity_percent")
        self.wind_speed_mps: float = _float("wind_speed_mps")
        self.dew_point_c: float = _float("dew_point_c")
        self.temperature_anomaly_c: float = _float("temperature_anomaly_c")
        self.humidity_anomaly_percent: float = _float("humidity_anomaly_percent")

        # Thermal Indices
        self.heat_index_c: float = _float("heat_index_c")
        self.heat_index_f: float = _float("heat_index_f")
        self.wbgt_c: float = _float("wbgt_c")
        self.wbgt_category: str = str(raw_data.get("wbgt_category", "")).strip()
        self.hours_above_heat_threshold: float = _float("hours_above_heat_threshold")
        self.nighttime_min_temperature_c: float = _float("nighttime_min_temperature_c")
        self.heatwave_day: bool = _bool("heatwave_day")
        self.consecutive_hot_days: int = _int("consecutive_hot_days")
        self.consecutive_heat_days: int = _int("consecutive_heat_days") or self.consecutive_hot_days
        self.heat_duration_hours: float = _float("heat_duration_hours")
        self.nighttime_heat_stress: float = _float("nighttime_heat_stress")
        self.humidity_burden: float = _float("humidity_burden")

        # Exposure & Vulnerability
        self.outdoor_exposure_index: float = _float("outdoor_exposure_index")
        self.urban_heat_index: float = _float("urban_heat_index")
        self.population_exposure_index: float = _float("population_exposure_index")
        self.vulnerability_index: float = _float("vulnerability_index")
        self.public_health_response_index: float = _float("public_health_response_index")
        self.healthcare_access_index: float = _float("healthcare_access_index")
        self.heat_action_plan_index: float = _float("heat_action_plan_index")
        self.cooling_access_index: float = _float("cooling_access_index")
        self.heat_exposure_index: float = _float("heat_exposure_index")

        # Lagged Exposure & Cumulative Heat
        self.heat_exposure_lag_1: float = _float("heat_exposure_lag_1")
        self.heat_exposure_lag_2: float = _float("heat_exposure_lag_2")
        self.heat_exposure_lag_3: float = _float("heat_exposure_lag_3")
        self.heat_exposure_lag_7: float = _float("heat_exposure_lag_7")
        self.cumulative_heat_load_3day: float = _float("cumulative_heat_load_3day")
        self.cumulative_heat_load_7day: float = _float("cumulative_heat_load_7day")

        # Synthetic Mortality Counts
        self.expected_heatstroke_deaths: float = _float("expected_heatstroke_deaths")
        self.expected_other_heat_related_deaths: float = _float("expected_other_heat_related_deaths")
        self.expected_heat_related_deaths: float = _float("expected_heat_related_deaths")
        self.heatstroke_deaths: int = _int("heatstroke_deaths")
        self.other_heat_related_deaths: int = _int("other_heat_related_deaths")
        self.heat_related_deaths_total: int = _int("heat_related_deaths_total")
        self.mortality_anomaly: float = _float("mortality_anomaly")

        # Mortality Rates
        self.heat_related_mortality_rate_per_100000: float = _float("heat_related_mortality_rate_per_100000")
        self.heatstroke_mortality_rate_per_100000: float = _float("heatstroke_mortality_rate_per_100000")

        # Age & Gender Breakdowns
        self.heat_related_deaths_under_30: int = _int("heat_related_deaths_under_30") or _int("deaths_under_30")
        self.heat_related_deaths_30_59: int = _int("heat_related_deaths_30_59") or _int("deaths_30_59")
        self.heat_related_deaths_60_plus: int = _int("heat_related_deaths_60_plus") or _int("deaths_60_plus")

        self.heat_related_deaths_male: int = _int("heat_related_deaths_male") or _int("deaths_male")
        self.heat_related_deaths_female: int = _int("heat_related_deaths_female") or _int("deaths_female")
        self.heatstroke_deaths_male: int = _int("heatstroke_deaths_male")
        self.heatstroke_deaths_female: int = _int("heatstroke_deaths_female")

        # Thermal signature
        self.thermal_signature: str = str(raw_data.get("thermal_signature", "")).strip()

        # Backward compatibility properties
        self.max_temperature_c: float = self.maximum_temperature_c
        self.min_temperature_c: float = self.minimum_temperature_c
        self.deaths_under_30: int = self.heat_related_deaths_under_30
        self.deaths_30_59: int = self.heat_related_deaths_30_59
        self.deaths_60_plus: int = self.heat_related_deaths_60_plus

    @property
    def demographics(self) -> Dict[str, Any]:
        return {
            "elderly_population_percent": self.elderly_population_percent,
            "working_age_population_percent": self.working_age_population_percent,
            "under_30_population_percent": self.under_30_population_percent,
            "outdoor_worker_fraction": self.outdoor_worker_fraction,
            "urban_population_percent": self.urban_population_percent
        }

    @property
    def weather(self) -> Dict[str, Any]:
        return {
            "maximum_temperature_c": self.maximum_temperature_c,
            "minimum_temperature_c": self.minimum_temperature_c,
            "mean_temperature_c": self.mean_temperature_c,
            "relative_humidity_percent": self.relative_humidity_percent,
            "wind_speed_mps": self.wind_speed_mps,
            "dew_point_c": self.dew_point_c,
            "temperature_anomaly_c": self.temperature_anomaly_c,
            "humidity_anomaly_percent": self.humidity_anomaly_percent
        }

    @property
    def thermal_indices(self) -> Dict[str, Any]:
        return {
            "heat_index_c": self.heat_index_c,
            "heat_index_f": self.heat_index_f,
            "wbgt_c": self.wbgt_c,
            "wbgt_category": self.wbgt_category,
            "hours_above_heat_threshold": self.hours_above_heat_threshold,
            "nighttime_min_temperature_c": self.nighttime_min_temperature_c,
            "heatwave_day": self.heatwave_day,
            "consecutive_hot_days": self.consecutive_hot_days,
            "consecutive_heat_days": self.consecutive_heat_days,
            "heat_duration_hours": self.heat_duration_hours,
            "nighttime_heat_stress": self.nighttime_heat_stress,
            "humidity_burden": self.humidity_burden
        }

    @property
    def exposure(self) -> Dict[str, Any]:
        return {
            "outdoor_exposure_index": self.outdoor_exposure_index,
            "urban_heat_index": self.urban_heat_index,
            "population_exposure_index": self.population_exposure_index,
            "heat_exposure_index": self.heat_exposure_index
        }

    @property
    def vulnerability(self) -> Dict[str, Any]:
        return {
            "vulnerability_index": self.vulnerability_index,
            "public_health_response_index": self.public_health_response_index,
            "healthcare_access_index": self.healthcare_access_index,
            "heat_action_plan_index": self.heat_action_plan_index,
            "cooling_access_index": self.cooling_access_index
        }

    @property
    def lagged_exposure(self) -> Dict[str, Any]:
        return {
            "heat_exposure_lag_1": self.heat_exposure_lag_1,
            "heat_exposure_lag_2": self.heat_exposure_lag_2,
            "heat_exposure_lag_3": self.heat_exposure_lag_3,
            "heat_exposure_lag_7": self.heat_exposure_lag_7,
            "cumulative_heat_load_3day": self.cumulative_heat_load_3day,
            "cumulative_heat_load_7day": self.cumulative_heat_load_7day
        }

    @property
    def mortality(self) -> Dict[str, Any]:
        return {
            "expected_heatstroke_deaths": self.expected_heatstroke_deaths,
            "expected_other_heat_related_deaths": self.expected_other_heat_related_deaths,
            "expected_heat_related_deaths": self.expected_heat_related_deaths,
            "heatstroke_deaths": self.heatstroke_deaths,
            "other_heat_related_deaths": self.other_heat_related_deaths,
            "heat_related_deaths_total": self.heat_related_deaths_total,
            "mortality_anomaly": self.mortality_anomaly,
            "heat_related_mortality_rate_per_100000": self.heat_related_mortality_rate_per_100000,
            "heatstroke_mortality_rate_per_100000": self.heatstroke_mortality_rate_per_100000
        }

    @property
    def age_breakdown(self) -> Dict[str, Any]:
        return {
            "heat_related_deaths_under_30": self.heat_related_deaths_under_30,
            "heat_related_deaths_30_59": self.heat_related_deaths_30_59,
            "heat_related_deaths_60_plus": self.heat_related_deaths_60_plus
        }

    @property
    def gender_breakdown(self) -> Dict[str, Any]:
        return {
            "heat_related_deaths_male": self.heat_related_deaths_male,
            "heat_related_deaths_female": self.heat_related_deaths_female,
            "heatstroke_deaths_male": self.heatstroke_deaths_male,
            "heatstroke_deaths_female": self.heatstroke_deaths_female
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to complete JSON-serializable dictionary with all 61 fields and groups."""
        return {
            "date": self.date,
            "state": self.state,
            "data_type": self.data_type,
            "population": self.population,
            # Weather
            "maximum_temperature_c": self.maximum_temperature_c,
            "minimum_temperature_c": self.minimum_temperature_c,
            "mean_temperature_c": self.mean_temperature_c,
            "relative_humidity_percent": self.relative_humidity_percent,
            "wind_speed_mps": self.wind_speed_mps,
            "dew_point_c": self.dew_point_c,
            "temperature_anomaly_c": self.temperature_anomaly_c,
            "humidity_anomaly_percent": self.humidity_anomaly_percent,
            # Thermal
            "heat_index_c": self.heat_index_c,
            "heat_index_f": self.heat_index_f,
            "wbgt_c": self.wbgt_c,
            "wbgt_category": self.wbgt_category,
            "hours_above_heat_threshold": self.hours_above_heat_threshold,
            "nighttime_min_temperature_c": self.nighttime_min_temperature_c,
            "heatwave_day": self.heatwave_day,
            "consecutive_hot_days": self.consecutive_hot_days,
            "consecutive_heat_days": self.consecutive_heat_days,
            "heat_duration_hours": self.heat_duration_hours,
            "nighttime_heat_stress": self.nighttime_heat_stress,
            "humidity_burden": self.humidity_burden,
            # Demographics
            "elderly_population_percent": self.elderly_population_percent,
            "working_age_population_percent": self.working_age_population_percent,
            "under_30_population_percent": self.under_30_population_percent,
            "outdoor_worker_fraction": self.outdoor_worker_fraction,
            "urban_population_percent": self.urban_population_percent,
            # Exposure & Vulnerability
            "outdoor_exposure_index": self.outdoor_exposure_index,
            "urban_heat_index": self.urban_heat_index,
            "population_exposure_index": self.population_exposure_index,
            "vulnerability_index": self.vulnerability_index,
            "public_health_response_index": self.public_health_response_index,
            "healthcare_access_index": self.healthcare_access_index,
            "heat_action_plan_index": self.heat_action_plan_index,
            "cooling_access_index": self.cooling_access_index,
            "heat_exposure_index": self.heat_exposure_index,
            # Lagged
            "heat_exposure_lag_1": self.heat_exposure_lag_1,
            "heat_exposure_lag_2": self.heat_exposure_lag_2,
            "heat_exposure_lag_3": self.heat_exposure_lag_3,
            "heat_exposure_lag_7": self.heat_exposure_lag_7,
            "cumulative_heat_load_3day": self.cumulative_heat_load_3day,
            "cumulative_heat_load_7day": self.cumulative_heat_load_7day,
            # Mortality
            "expected_heatstroke_deaths": self.expected_heatstroke_deaths,
            "expected_other_heat_related_deaths": self.expected_other_heat_related_deaths,
            "expected_heat_related_deaths": self.expected_heat_related_deaths,
            "heatstroke_deaths": self.heatstroke_deaths,
            "other_heat_related_deaths": self.other_heat_related_deaths,
            "heat_related_deaths_total": self.heat_related_deaths_total,
            "mortality_anomaly": self.mortality_anomaly,
            "heat_related_mortality_rate_per_100000": self.heat_related_mortality_rate_per_100000,
            "heatstroke_mortality_rate_per_100000": self.heatstroke_mortality_rate_per_100000,
            # Age & Gender
            "heat_related_deaths_under_30": self.heat_related_deaths_under_30,
            "heat_related_deaths_30_59": self.heat_related_deaths_30_59,
            "heat_related_deaths_60_plus": self.heat_related_deaths_60_plus,
            "heat_related_deaths_male": self.heat_related_deaths_male,
            "heat_related_deaths_female": self.heat_related_deaths_female,
            "heatstroke_deaths_male": self.heatstroke_deaths_male,
            "heatstroke_deaths_female": self.heatstroke_deaths_female,
            "thermal_signature": self.thermal_signature,
            # Aliases for backward compatibility
            "max_temperature_c": self.maximum_temperature_c,
            "min_temperature_c": self.minimum_temperature_c,
            "deaths_under_30": self.heat_related_deaths_under_30,
            "deaths_30_59": self.heat_related_deaths_30_59,
            "deaths_60_plus": self.heat_related_deaths_60_plus,
            # Internal normalized structures
            "demographics": self.demographics,
            "weather": self.weather,
            "thermal_indices": self.thermal_indices,
            "exposure": self.exposure,
            "vulnerability": self.vulnerability,
            "lagged_exposure": self.lagged_exposure,
            "mortality": self.mortality,
            "age_breakdown": self.age_breakdown,
            "gender_breakdown": self.gender_breakdown
        }


class MortalityDataProvider(ABC):
    """
    Abstract base class establishing the contract for mortality data sources.
    Decouples analysis logic from file formats, versions, or AI generation sources.
    """
    @abstractmethod
    def load(self) -> None:
        """Load and parse records into memory."""
        pass

    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate dataset integrity according to ClimateGuard standards."""
        pass

    @abstractmethod
    def get_records(self, state: Optional[str] = None) -> List[MortalityRecord]:
        """Return all parsed records, optionally filtered by state."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return dataset metadata, versioning, and provider information."""
        pass


class SyntheticCSVProvider(MortalityDataProvider):
    """
    Concrete provider implementation for synthetic CSV mortality datasets.
    Handles schema mapping, 61-column parsing, and validation.
    """
    def __init__(
        self,
        filepath: Optional[Path] = None,
        dataset_name: str = "mortality_synthetic_daily",
        dataset_version: Optional[str] = None,
        generated_by: Optional[str] = None,
        dataset_provider: str = "synthetic"
    ):
        self.filepath = filepath or self._resolve_default_filepath()
        self.dataset_name = dataset_name
        self.dataset_version = dataset_version or os.getenv("MORTALITY_DATA_VERSION", "claude_v1")
        self.generated_by = generated_by or ("Claude" if "claude" in self.dataset_version.lower() else "Synthetic Engine")
        self.dataset_provider = dataset_provider
        self.records: List[MortalityRecord] = []
        self._is_loaded = False
        self._validation_errors: List[str] = []

    def _resolve_default_filepath(self) -> Path:
        """Resolve file path from environment variable or standard locations."""
        env_file = os.getenv("MORTALITY_DATA_FILE", "").strip()
        if env_file:
            p = Path(env_file)
            if p.exists():
                return p
            p_sub = DEFAULT_MORTALITY_DIR / env_file
            if p_sub.exists():
                return p_sub
            p_root = BASE_DIR.parent / env_file
            if p_root.exists():
                return p_root

        primary = DEFAULT_MORTALITY_DIR / DEFAULT_CSV_FILENAME
        if primary.exists():
            return primary
        fallback_root = BASE_DIR.parent / DEFAULT_CSV_FILENAME
        if fallback_root.exists():
            return fallback_root
        return primary

    def load(self) -> None:
        """Load and parse records from CSV file."""
        if not self.filepath.exists():
            err = f"Mortality dataset file missing at {self.filepath}"
            logger.error(err)
            self._validation_errors.append(err)
            raise FileNotFoundError(err)

        loaded_records: List[MortalityRecord] = []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = MortalityRecord.from_csv_row(row)
                    loaded_records.append(record)

            self.records = loaded_records
            self._is_loaded = True
            logger.info(f"Loaded {len(self.records)} mortality records from {self.filepath.name}")

            is_valid, errors = self.validate()
            if not is_valid:
                logger.warning(f"Mortality dataset validation issues: {errors}")
        except Exception as exc:
            err_msg = f"Failed to parse mortality CSV {self.filepath}: {exc}"
            logger.error(err_msg)
            self._validation_errors.append(err_msg)
            raise RuntimeError(err_msg)

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate dataset according to Section 6 of specification:
        - Record count: 1,095
        - States: Tamil Nadu (365), Karnataka (365), Kerala (365)
        - data_type: SYNTHETIC
        - Date range: 2025-09-24 to 2026-09-23
        - Field validity:
          population > 0
          relative_humidity_percent: 0-100
          temperatures numeric
          WBGT numeric
          heat-related death counts >= 0
          mortality rates >= 0
        - Logs clear validation errors without silently modifying invalid records.
        """
        errors: List[str] = []
        if not self.records:
            return False, ["Dataset is empty or not loaded"]

        # 1. Record count
        if len(self.records) != 1095:
            errors.append(f"Expected 1,095 records, found {len(self.records)}")

        # 2. States verification
        states_found = set(r.state for r in self.records)
        expected_states = {"Tamil Nadu", "Karnataka", "Kerala"}
        missing_states = expected_states - states_found
        if missing_states:
            errors.append(f"Missing expected states: {missing_states}")

        # Check each state count
        for state in expected_states:
            count = sum(1 for r in self.records if r.state == state)
            if count != 365:
                errors.append(f"State '{state}' expected 365 records, found {count}")

        # 3. Date range validation (2025-09-24 to 2026-09-23 for Claude dataset)
        dates = [r.date for r in self.records if r.date]
        if dates:
            min_date, max_date = min(dates), max(dates)
            expected_min = "2025-09-24"
            expected_max = "2026-09-23"
            if min_date != expected_min or max_date != expected_max:
                # If using a synthetic dataset with a different annual slice, log clearly
                errors.append(f"Expected date range {expected_min} to {expected_max}, found {min_date} to {max_date}")

        # 4. Record-level validation
        for idx, r in enumerate(self.records):
            if r.population <= 0:
                errors.append(f"Row {idx+1}: invalid population ({r.population})")
                break
            if not (0.0 <= r.relative_humidity_percent <= 100.0):
                errors.append(f"Row {idx+1}: humidity outside 0-100% ({r.relative_humidity_percent})")
                break
            if r.wind_speed_mps < 0.0:
                errors.append(f"Row {idx+1}: negative wind speed ({r.wind_speed_mps})")
                break
            if r.heat_related_deaths_total < 0:
                errors.append(f"Row {idx+1}: negative heat related deaths ({r.heat_related_deaths_total})")
                break
            if r.heat_related_mortality_rate_per_100000 < 0:
                errors.append(f"Row {idx+1}: negative mortality rate ({r.heat_related_mortality_rate_per_100000})")
                break
            if r.data_type.upper() != "SYNTHETIC":
                errors.append(f"Row {idx+1}: data_type must be SYNTHETIC, found '{r.data_type}'")
                break

        self._validation_errors = errors
        return (len(errors) == 0, errors)

    def get_records(self, state: Optional[str] = None) -> List[MortalityRecord]:
        """Return loaded records, filtered by state if requested."""
        if not self._is_loaded:
            self.load()
        if not state or state.lower() == "all":
            return self.records
        state_clean = state.strip().lower()
        return [r for r in self.records if r.state.lower() == state_clean]

    def get_metadata(self) -> Dict[str, Any]:
        """Return dataset version, provenance, and operational status."""
        dates = [r.date for r in self.records if r.date]
        min_date = min(dates) if dates else "2025-09-24"
        max_date = max(dates) if dates else "2026-09-23"
        states = list(set(r.state for r in self.records))

        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "dataset_provider": self.dataset_provider,
            "generated_by": self.generated_by,
            "file_source": self.filepath.name,
            "record_count": len(self.records),
            "date_range": f"{min_date} to {max_date}",
            "states": states,
            "data_type": "SYNTHETIC",
            "is_valid": len(self._validation_errors) == 0,
            "validation_errors": self._validation_errors,
            "scientific_disclaimer": (
                "Mortality figures shown by ClimateGuard are synthetic research simulation data "
                "used for prototype health-impact analysis. They are not official government records "
                "(NCRB/IMD), verified deaths, or individual medical-risk predictions."
            )
        }


# Global Provider Singleton Instance
_mortality_provider_instance: Optional[MortalityDataProvider] = None


def get_mortality_provider() -> MortalityDataProvider:
    """Returns or lazily instantiates the active configured mortality provider."""
    global _mortality_provider_instance
    if _mortality_provider_instance is None:
        file_name = os.getenv("MORTALITY_DATA_FILE", DEFAULT_CSV_FILENAME).strip()
        version = os.getenv("MORTALITY_DATA_VERSION", "claude_v1").strip()
        provider_type = os.getenv("MORTALITY_DATA_TYPE", "SYNTHETIC").strip()
        generator = "Claude" if "claude" in version.lower() else "Synthetic Engine"

        provider = SyntheticCSVProvider(
            filepath=DEFAULT_MORTALITY_DIR / file_name if not Path(file_name).is_absolute() else Path(file_name),
            dataset_name="mortality_synthetic_daily",
            dataset_version=version,
            generated_by=generator,
            dataset_provider=provider_type.lower()
        )
        try:
            provider.load()
        except Exception as exc:
            logger.warning(f"Could not initialize mortality provider: {exc}")
        _mortality_provider_instance = provider
    return _mortality_provider_instance


def set_mortality_provider(provider: MortalityDataProvider) -> None:
    """Allows runtime or test swapping of the mortality data provider."""
    global _mortality_provider_instance
    _mortality_provider_instance = provider


def reset_mortality_provider() -> None:
    """Resets the singleton provider instance for test isolation."""
    global _mortality_provider_instance
    _mortality_provider_instance = None


class HistoricalAnalogueService:
    """
    Computes weighted normalized Euclidean distances across multidimensional thermal signatures
    to identify the top 5 most similar historical synthetic days for a given district condition.

    Uses 10 normalized variables:
    - maximum temperature
    - mean temperature
    - humidity
    - WBGT
    - Heat Index
    - wind speed
    - heat duration
    - consecutive hot days
    - nighttime heat stress
    - cumulative heat load
    """
    WEIGHTS = {
        "wbgt": 0.25,             # Primary human thermal stress index
        "temp": 0.20,             # Ambient maximum air temperature
        "mean_temp": 0.10,        # Mean diurnal temperature
        "heat_index": 0.15,       # Apparent temperature
        "humidity": 0.10,         # Relative humidity
        "wind": 0.05,             # Surface wind speed
        "heat_duration": 0.05,    # Hours of severe heat
        "consecutive": 0.05,      # Consecutive hot days
        "nighttime": 0.025,       # Nighttime heat stress
        "cumulative_load": 0.025  # 7-day cumulative heat load
    }

    BOUNDS = {
        "wbgt": (20.0, 38.0),
        "temp": (20.0, 48.0),
        "mean_temp": (18.0, 42.0),
        "heat_index": (22.0, 52.0),
        "humidity": (20.0, 100.0),
        "wind": (0.0, 15.0),
        "heat_duration": (0.0, 14.0),
        "consecutive": (0.0, 10.0),
        "nighttime": (0.0, 1.0),
        "cumulative_load": (0.0, 50.0)
    }

    @classmethod
    def _normalize(cls, val: float, key: str) -> float:
        min_v, max_v = cls.BOUNDS[key]
        clamped = max(min_v, min(max_v, float(val)))
        return (clamped - min_v) / (max_v - min_v)

    @classmethod
    def find_analogues(
        cls,
        state: str,
        current_temp: float,
        current_humidity: float,
        current_wbgt: float,
        current_hi: Optional[float] = None,
        current_wind: float = 3.0,
        current_mean_temp: Optional[float] = None,
        heat_duration: float = 6.0,
        consecutive_heat_days: int = 0,
        nighttime_heat_stress: float = 0.3,
        cumulative_heat_load_7day: float = 12.0,
        top_n: int = 5,
        provider: Optional[MortalityDataProvider] = None
    ) -> Dict[str, Any]:
        """
        Identify top_n most similar historical synthetic records for the given thermal signature.
        """
        if current_hi is None:
            current_hi = round(current_temp + 0.33 * (current_humidity / 100.0 * 20.0), 1)
        if current_mean_temp is None:
            current_mean_temp = round(current_temp - 4.5, 1)

        active_provider = provider or get_mortality_provider()
        candidates = active_provider.get_records(state=state)

        # If state was specified but not found in records, return unavailable with clear error
        if not candidates:
            return {
                "available": False,
                "data_type": "SYNTHETIC",
                "state_scope": state,
                "error": f"No synthetic records found for state '{state}'",
                "disclaimer": "Historical health-impact analysis temporarily unavailable."
            }

        # Normalize target conditions
        t_norm = cls._normalize(current_temp, "temp")
        mt_norm = cls._normalize(current_mean_temp, "mean_temp")
        wbgt_norm = cls._normalize(current_wbgt, "wbgt")
        hi_norm = cls._normalize(current_hi, "heat_index")
        rh_norm = cls._normalize(current_humidity, "humidity")
        w_norm = cls._normalize(current_wind, "wind")
        dur_norm = cls._normalize(heat_duration, "heat_duration")
        c_norm = cls._normalize(float(consecutive_heat_days), "consecutive")
        nt_norm = cls._normalize(nighttime_heat_stress, "nighttime")
        load_norm = cls._normalize(cumulative_heat_load_7day, "cumulative_load")

        scored: List[Tuple[float, MortalityRecord]] = []
        for rec in candidates:
            r_t = cls._normalize(rec.maximum_temperature_c, "temp")
            r_mt = cls._normalize(rec.mean_temperature_c, "mean_temp")
            r_wbgt = cls._normalize(rec.wbgt_c, "wbgt")
            r_hi = cls._normalize(rec.heat_index_c, "heat_index")
            r_rh = cls._normalize(rec.relative_humidity_percent, "humidity")
            r_w = cls._normalize(rec.wind_speed_mps, "wind")
            r_dur = cls._normalize(rec.heat_duration_hours or 6.0, "heat_duration")
            r_c = cls._normalize(float(rec.consecutive_heat_days), "consecutive")
            r_nt = cls._normalize(rec.nighttime_heat_stress or 0.3, "nighttime")
            r_load = cls._normalize(rec.cumulative_heat_load_7day or 10.0, "cumulative_load")

            # Weighted Euclidean distance
            dist_sq = (
                cls.WEIGHTS["wbgt"] * ((wbgt_norm - r_wbgt) ** 2) +
                cls.WEIGHTS["temp"] * ((t_norm - r_t) ** 2) +
                cls.WEIGHTS["mean_temp"] * ((mt_norm - r_mt) ** 2) +
                cls.WEIGHTS["heat_index"] * ((hi_norm - r_hi) ** 2) +
                cls.WEIGHTS["humidity"] * ((rh_norm - r_rh) ** 2) +
                cls.WEIGHTS["wind"] * ((w_norm - r_w) ** 2) +
                cls.WEIGHTS["heat_duration"] * ((dur_norm - r_dur) ** 2) +
                cls.WEIGHTS["consecutive"] * ((c_norm - r_c) ** 2) +
                cls.WEIGHTS["nighttime"] * ((nt_norm - r_nt) ** 2) +
                cls.WEIGHTS["cumulative_load"] * ((load_norm - r_load) ** 2)
            )
            dist = math.sqrt(dist_sq)

            # Convert distance to similarity percentage (0-100)
            similarity = max(0.0, min(100.0, round((1.0 - dist) * 100, 1)))
            scored.append((similarity, rec))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored[:top_n]

        # Extract analogues details
        analogues_list = []
        sim_scores = []
        deaths_list = []
        rates_list = []
        u30_total = 0
        m30_59_total = 0
        o60_total = 0
        male_total = 0
        female_total = 0

        for sim, r in top_matches:
            sim_scores.append(sim)
            deaths_list.append(r.heat_related_deaths_total)
            rates_list.append(r.heat_related_mortality_rate_per_100000)
            u30_total += r.heat_related_deaths_under_30
            m30_59_total += r.heat_related_deaths_30_59
            o60_total += r.heat_related_deaths_60_plus
            male_total += r.heat_related_deaths_male
            female_total += r.heat_related_deaths_female

            try:
                date_obj = datetime.strptime(r.date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d %b %Y")
            except Exception:
                formatted_date = r.date

            analogues_list.append({
                "date": r.date,
                "formatted_date": formatted_date,
                "state": r.state,
                "similarity_score": sim,
                "maximum_temperature_c": r.maximum_temperature_c,
                "max_temperature_c": r.maximum_temperature_c,
                "mean_temperature_c": r.mean_temperature_c,
                "relative_humidity_percent": r.relative_humidity_percent,
                "wbgt_c": r.wbgt_c,
                "heat_index_c": r.heat_index_c,
                "heatwave_day": r.heatwave_day,
                "consecutive_heat_days": r.consecutive_heat_days,
                "vulnerability_index": r.vulnerability_index,
                "heat_related_deaths_total": r.heat_related_deaths_total,
                "heat_related_mortality_rate_per_100000": r.heat_related_mortality_rate_per_100000,
                "heat_related_deaths_under_30": r.heat_related_deaths_under_30,
                "heat_related_deaths_30_59": r.heat_related_deaths_30_59,
                "heat_related_deaths_60_plus": r.heat_related_deaths_60_plus,
                "heat_related_deaths_male": r.heat_related_deaths_male,
                "heat_related_deaths_female": r.heat_related_deaths_female
            })

        # Calculate aggregates
        count = len(analogues_list)
        avg_sim = round(sum(sim_scores) / count, 1) if count else 0.0
        avg_deaths = round(sum(deaths_list) / count, 1) if count else 0.0
        deaths_sorted = sorted(deaths_list)
        median_deaths = (
            deaths_sorted[count // 2]
            if count % 2 == 1
            else round((deaths_sorted[count // 2 - 1] + deaths_sorted[count // 2]) / 2, 1)
        ) if count else 0.0

        min_deaths = min(deaths_list) if deaths_list else 0
        max_deaths = max(deaths_list) if deaths_list else 0
        avg_rate = round(sum(rates_list) / count, 2) if count else 0.0

        total_age_deaths = u30_total + m30_59_total + o60_total
        if total_age_deaths > 0:
            u30_pct = round((u30_total / total_age_deaths) * 100, 1)
            m30_59_pct = round((m30_59_total / total_age_deaths) * 100, 1)
            o60_pct = round((o60_total / total_age_deaths) * 100, 1)
        else:
            u30_pct, m30_59_pct, o60_pct = 10.0, 60.0, 30.0

        total_gender_deaths = male_total + female_total
        if total_gender_deaths > 0:
            male_pct = round((male_total / total_gender_deaths) * 100, 1)
            female_pct = round((female_total / total_gender_deaths) * 100, 1)
        else:
            male_pct, female_pct = 55.0, 45.0

        if o60_pct >= m30_59_pct and o60_pct >= u30_pct:
            most_affected = "Older Adults (60+ Years)"
        elif m30_59_pct >= o60_pct:
            most_affected = "Adults in Labor Force (30-59 Years)"
        else:
            most_affected = "Younger Demographics (Under 30)"

        # Formulate a concise inference for subtle UI display (Section 8)
        if avg_rate >= 0.15 or current_wbgt >= 32.0:
            analogue_level = "Elevated"
            concise_inference = "Historical thermal analogues suggest elevated heat-related health burden."
        elif avg_rate >= 0.08 or current_wbgt >= 30.0:
            analogue_level = "Moderate"
            concise_inference = "Historical thermal analogues suggest moderate heat-health burden under sustained exposure."
        else:
            analogue_level = "Low"
            concise_inference = "Historical thermal analogues indicate baseline heat-health impact."

        summary = {
            "count": count,
            "average_similarity": avg_sim,
            "min_similarity": min(sim_scores) if sim_scores else 0.0,
            "max_similarity": max(sim_scores) if sim_scores else 0.0,
            "average_simulated_deaths": avg_deaths,
            "median_simulated_deaths": median_deaths,
            "min_simulated_deaths": min_deaths,
            "max_simulated_deaths": max_deaths,
            "average_mortality_rate_per_100000": avg_rate,
            "analogue_level": analogue_level,
            "concise_inference": concise_inference,
            "most_affected_age_group": most_affected,
            "age_distribution": {
                "under_30_percent": u30_pct,
                "30_59_percent": m30_59_pct,
                "60_plus_percent": o60_pct
            },
            "gender_distribution": {
                "male_percent": male_pct,
                "female_percent": female_pct
            }
        }

        return {
            "available": True,
            "data_type": "SYNTHETIC",
            "state_scope": state,
            "analogues": analogues_list,
            "summary": summary,
            "concise_inference": concise_inference,
            "analogue_level": analogue_level,
            "disclaimer": (
                "Historical synthetic simulation data with similar thermal conditions showed "
                "elevated simulated heat-health burden. Not an individual mortality prediction."
            )
        }


class HealthImpactAnalysisService:
    """
    Synthesizes environmental thermal observations, demographic profile multipliers,
    and historical synthetic mortality analogues into a unified decision-support assessment.
    """
    @classmethod
    def analyze_district(
        cls,
        district: Dict[str, Any],
        profile_id: str = "general_public"
    ) -> Dict[str, Any]:
        """
        Generate complete health impact analysis for a district.
        """
        state = district.get("state", "Tamil Nadu")
        temp = float(district.get("temperature", district.get("temp", 32.0)))
        rh = float(district.get("humidity", district.get("rh", 60.0)))
        wind = float(district.get("wind_speed", district.get("wind", 3.0)))
        wbgt = float(district.get("wbgt", 30.0))
        hi = float(district.get("heat_index", district.get("hi", 35.0)))
        hss = int(district.get("heat_stress_score", 50))
        category = district.get("category", "Danger")

        # 1. Historical analogue matching
        analogue_res = HistoricalAnalogueService.find_analogues(
            state=state,
            current_temp=temp,
            current_humidity=rh,
            current_wbgt=wbgt,
            current_hi=hi,
            current_wind=wind,
            top_n=5
        )

        # 2. Profile-specific impact computation
        profile_impact_calc = calculate_profile_impact(
            wbgt=wbgt,
            temp=temp,
            rh=rh,
            profile_id=profile_id
        )

        # 3. Profile-specific concise interpretation
        interpretation_bullets = cls._generate_interpretation(
            profile_id=profile_id,
            category=category,
            wbgt=wbgt,
            analogue_summary=analogue_res.get("summary")
        )

        conditions_dict = {
            "temperature_c": temp,
            "humidity_percent": rh,
            "wind_speed_mps": wind,
            "heat_index_c": hi,
            "wbgt_c": wbgt,
            "heat_stress_score": hss,
            "risk": category.upper(),
            "category": category,
            "risk_category": category,
            "color": district.get("color", "#f97316")
        }

        analogue_summary = analogue_res.get("summary")
        analogues_available = analogue_res.get("available", False)
        if analogue_summary and analogues_available:
            analogue_summary["available"] = True

        bulletin_data = profile_impact_calc.get("bulletin", {})
        # Attach concise historical context to bulletin
        if analogue_summary:
            bulletin_data["historical_context"] = analogue_summary.get(
                "concise_inference",
                "Historical thermal analogues suggest elevated heat-health burden."
            )
            bulletin_data["analogue_level"] = analogue_summary.get("analogue_level", "Elevated")

        return {
            "district": district.get("name") or district.get("district") or district.get("id"),
            "district_id": district.get("id"),
            "district_name": district.get("name") or district.get("district"),
            "state": state,
            "current_conditions": conditions_dict,
            "environmental_conditions": conditions_dict,
            "mortality_dataset": {
                "type": "SYNTHETIC",
                "version": get_mortality_provider().get_metadata().get("dataset_version", "claude_v1"),
                "status": "Available" if analogues_available else "Unavailable"
            },
            "historical_analogues": analogue_summary if analogues_available else {
                "available": False,
                "message": "Historical health-impact analysis temporarily unavailable."
            },
            "age_context": analogue_summary.get("age_distribution") if analogue_summary else None,
            "top_scenarios": analogue_res.get("analogues", []),
            "profile": profile_impact_calc.get("profile_name", profile_id),
            "profile_id": profile_id,
            "impact_level": profile_impact_calc.get("impact_level", "HIGH"),
            "interpretation": interpretation_bullets,
            "bulletin": bulletin_data,
            "disclaimer": (
                "Historical synthetic scenarios with similar thermal conditions showed "
                "elevated simulated heat-health burden. Not an individual mortality prediction."
            ),
            "scientific_disclaimer": (
                "Mortality figures shown by ClimateGuard are synthetic simulation data "
                "used for prototype health-impact analysis. They are not official mortality "
                "observations or individual medical-risk predictions."
            )
        }

    @classmethod
    def _generate_interpretation(
        cls,
        profile_id: str,
        category: str,
        wbgt: float,
        analogue_summary: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Formulates targeted public health interpretation bullets."""
        bullets = []
        is_high = category in ["Danger", "Extreme Danger", "Severe"]

        # Synthetic analogue context (subtle and concise)
        if analogue_summary:
            inference = analogue_summary.get("concise_inference", "Historical thermal analogues suggest elevated heat-health burden.")
            bullets.append(inference)

        # Profile-specific exposure context
        if profile_id == "it_office":
            bullets.append("Indoor climate-controlled workers experience lower sustained exposure, but commute windows (12:00 PM – 4:00 PM) create acute dehydration and thermal shock risk.")
            if is_high:
                bullets.append("Ensure office air-handling ventilation backup; stay hydrated with electrolytes despite air conditioning.")
        elif profile_id in ["construction_labor", "outdoor_worker"]:
            bullets.append("Heavy physical exertion under direct radiant solar load exponentially magnifies cardiovascular strain beyond ambient air readings.")
            if is_high:
                bullets.append("Mandatory shade breaks and cessation of peak-sun heavy tasks are strongly advised.")
        elif profile_id == "elderly":
            bullets.append("Reduced physiological thirst responsiveness and impaired vascular heat dissipation elevate heat-illness risks significantly.")
            bullets.append("Maintain dedicated indoor cooling and regular family check-ins.")
        elif profile_id == "pregnant":
            bullets.append("Elevated core metabolic heat and fluid-shift sensitivity require continuous hydration and avoidance of unshaded outdoor spaces.")
        elif profile_id == "child":
            bullets.append("Higher surface-area-to-body-mass ratio accelerates dehydration in young children; restrict strenuous outdoor playground sports during midday.")
        else:
            bullets.append("Sustained outdoor activities without scheduled shade breaks carry risk of heat exhaustion, cramps, and elevated cardiovascular fatigue.")

        return bullets
