from pathlib import Path

import pytest

from cps_sentinel.config import ConfigurationError, load_settings

ROOT = Path(__file__).resolve().parents[1]


def test_default_configuration_loads() -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")

    assert settings.project_name == "CPS Sentinel"
    assert settings.random_seed == 42
    assert settings.simulation.duration_hours == 24
    assert settings.simulation.start_time.utcoffset() is not None
    assert settings.simulation.profiles.pv_peak_kw == 6.0
    assert settings.simulation.battery.minimum_soc < settings.simulation.battery.maximum_soc
    assert settings.detection.physics_min_votes == 1
    assert settings.risk.impact_weight == 0.40
    assert settings.health.end_of_life_capacity_ah == 1.4
    assert settings.swat.persistence_votes == 3


def test_missing_configuration_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_settings(tmp_path / "missing.yaml")


def test_invalid_soc_limits_are_rejected(tmp_path: Path) -> None:
    config = tmp_path / "invalid.yaml"
    config.write_text(
        """
project:
  name: Test
  random_seed: 1
simulation:
  start_time: "2026-01-01T00:00:00+00:00"
  duration_hours: 1
  timestep_minutes: 5
  profiles:
    pv_peak_kw: 6
    pv_variability_fraction: 0.1
    load_base_kw: 1
    load_morning_peak_kw: 1
    load_evening_peak_kw: 1
    load_noise_std_kw: 0.1
  battery:
    capacity_kwh: 10
    initial_soc: 0.5
    minimum_soc: 0.9
    maximum_soc: 0.1
    maximum_power_kw: 5
    charge_efficiency: 0.95
    discharge_efficiency: 0.95
detection:
  robust_z_threshold: 3.5
  calibration_quantile: 0.995
  physics_min_votes: 1
  ml_score_percentile: 0.995
  persistence_window: 3
  persistence_votes: 2
  isolation_estimators: 200
risk:
  confidence_weight: 0.30
  impact_weight: 0.40
  duration_weight: 0.15
  safety_proximity_weight: 0.15
  grid_impact_reference_kw: 5
  soc_divergence_reference: 0.20
  duration_reference_steps: 36
  medium_threshold: 30
  high_threshold: 55
  critical_threshold: 80
health:
  rated_capacity_ah: 2.0
  end_of_life_capacity_ah: 1.4
  warning_soh_fraction: 0.80
  critical_soh_fraction: 0.70
  minimum_regression_cycles: 20
  regression_window_cycles: 60
swat:
  training_fraction: 0.80
  score_quantile: 0.995
  isolation_estimators: 200
  max_training_rows: 100000
  persistence_window: 5
  persistence_votes: 3
  event_gap_steps: 2
  top_contributors: 5
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="SOC limits"):
        load_settings(config)
