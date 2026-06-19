from pathlib import Path

import pytest

from cps_sentinel.config import ConfigurationError, load_settings

ROOT = Path(__file__).resolve().parents[1]


def test_default_configuration_loads() -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")

    assert settings.project_name == "CPS Sentinel"
    assert settings.random_seed == 42
    assert settings.simulation.duration_hours == 24
    assert settings.simulation.battery.minimum_soc < settings.simulation.battery.maximum_soc


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
  duration_hours: 1
  timestep_minutes: 5
  battery:
    capacity_kwh: 10
    initial_soc: 0.5
    minimum_soc: 0.9
    maximum_soc: 0.1
    maximum_power_kw: 5
    charge_efficiency: 0.95
    discharge_efficiency: 0.95
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="SOC limits"):
        load_settings(config)
