"""Configuration loading and validation for CPS Sentinel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when project configuration is missing or invalid."""


@dataclass(frozen=True)
class BatteryConfig:
    capacity_kwh: float
    initial_soc: float
    minimum_soc: float
    maximum_soc: float
    maximum_power_kw: float
    charge_efficiency: float
    discharge_efficiency: float


@dataclass(frozen=True)
class SimulationConfig:
    duration_hours: int
    timestep_minutes: int
    battery: BatteryConfig


@dataclass(frozen=True)
class Settings:
    project_name: str
    random_seed: int
    simulation: SimulationConfig


def _require(mapping: dict[str, Any], key: str, section: str) -> Any:
    try:
        return mapping[key]
    except KeyError as exc:
        raise ConfigurationError(f"Missing '{section}.{key}'") from exc


def load_settings(path: str | Path) -> Settings:
    """Load and validate the stable subset of project configuration."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a mapping")

    project = _require(raw, "project", "root")
    simulation = _require(raw, "simulation", "root")
    if not isinstance(project, dict) or not isinstance(simulation, dict):
        raise ConfigurationError("Project and simulation sections must be mappings")

    battery = _require(simulation, "battery", "simulation")
    if not isinstance(battery, dict):
        raise ConfigurationError("simulation.battery must be a mapping")

    battery_config = BatteryConfig(
        capacity_kwh=float(_require(battery, "capacity_kwh", "simulation.battery")),
        initial_soc=float(_require(battery, "initial_soc", "simulation.battery")),
        minimum_soc=float(_require(battery, "minimum_soc", "simulation.battery")),
        maximum_soc=float(_require(battery, "maximum_soc", "simulation.battery")),
        maximum_power_kw=float(_require(battery, "maximum_power_kw", "simulation.battery")),
        charge_efficiency=float(
            _require(battery, "charge_efficiency", "simulation.battery")
        ),
        discharge_efficiency=float(
            _require(battery, "discharge_efficiency", "simulation.battery")
        ),
    )
    _validate_battery(battery_config)

    simulation_config = SimulationConfig(
        duration_hours=int(_require(simulation, "duration_hours", "simulation")),
        timestep_minutes=int(_require(simulation, "timestep_minutes", "simulation")),
        battery=battery_config,
    )
    if simulation_config.duration_hours <= 0 or simulation_config.timestep_minutes <= 0:
        raise ConfigurationError("Simulation duration and timestep must be positive")

    return Settings(
        project_name=str(_require(project, "name", "project")),
        random_seed=int(_require(project, "random_seed", "project")),
        simulation=simulation_config,
    )


def _validate_battery(config: BatteryConfig) -> None:
    if config.capacity_kwh <= 0 or config.maximum_power_kw <= 0:
        raise ConfigurationError("Battery capacity and maximum power must be positive")
    if not 0 <= config.minimum_soc < config.maximum_soc <= 1:
        raise ConfigurationError("Battery SOC limits must satisfy 0 <= min < max <= 1")
    if not config.minimum_soc <= config.initial_soc <= config.maximum_soc:
        raise ConfigurationError("Initial SOC must be within configured limits")
    if not 0 < config.charge_efficiency <= 1 or not 0 < config.discharge_efficiency <= 1:
        raise ConfigurationError("Battery efficiencies must be in the interval (0, 1]")
