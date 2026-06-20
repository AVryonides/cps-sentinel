"""Configuration loading and validation for CPS Sentinel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
class ProfileConfig:
    pv_peak_kw: float
    pv_variability_fraction: float
    load_base_kw: float
    load_morning_peak_kw: float
    load_evening_peak_kw: float
    load_noise_std_kw: float


@dataclass(frozen=True)
class SimulationConfig:
    start_time: datetime
    duration_hours: int
    timestep_minutes: int
    profiles: ProfileConfig
    battery: BatteryConfig


@dataclass(frozen=True)
class DetectionConfig:
    robust_z_threshold: float
    calibration_quantile: float
    physics_min_votes: int
    ml_score_percentile: float
    persistence_window: int
    persistence_votes: int
    isolation_estimators: int


@dataclass(frozen=True)
class RiskConfig:
    confidence_weight: float
    impact_weight: float
    duration_weight: float
    safety_proximity_weight: float
    grid_impact_reference_kw: float
    soc_divergence_reference: float
    duration_reference_steps: int
    medium_threshold: float
    high_threshold: float
    critical_threshold: float


@dataclass(frozen=True)
class Settings:
    project_name: str
    random_seed: int
    simulation: SimulationConfig
    detection: DetectionConfig
    risk: RiskConfig


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
    detection = _require(raw, "detection", "root")
    risk = _require(raw, "risk", "root")
    if (
        not isinstance(project, dict)
        or not isinstance(simulation, dict)
        or not isinstance(detection, dict)
        or not isinstance(risk, dict)
    ):
        raise ConfigurationError(
            "Project, simulation, detection, and risk sections must be mappings"
        )

    battery = _require_mapping(simulation, "battery", "simulation")
    profiles = _require_mapping(simulation, "profiles", "simulation")

    battery_config = BatteryConfig(
        capacity_kwh=float(_require(battery, "capacity_kwh", "simulation.battery")),
        initial_soc=float(_require(battery, "initial_soc", "simulation.battery")),
        minimum_soc=float(_require(battery, "minimum_soc", "simulation.battery")),
        maximum_soc=float(_require(battery, "maximum_soc", "simulation.battery")),
        maximum_power_kw=float(_require(battery, "maximum_power_kw", "simulation.battery")),
        charge_efficiency=float(_require(battery, "charge_efficiency", "simulation.battery")),
        discharge_efficiency=float(_require(battery, "discharge_efficiency", "simulation.battery")),
    )
    _validate_battery(battery_config)

    profile_config = ProfileConfig(
        pv_peak_kw=float(_require(profiles, "pv_peak_kw", "simulation.profiles")),
        pv_variability_fraction=float(
            _require(profiles, "pv_variability_fraction", "simulation.profiles")
        ),
        load_base_kw=float(_require(profiles, "load_base_kw", "simulation.profiles")),
        load_morning_peak_kw=float(
            _require(profiles, "load_morning_peak_kw", "simulation.profiles")
        ),
        load_evening_peak_kw=float(
            _require(profiles, "load_evening_peak_kw", "simulation.profiles")
        ),
        load_noise_std_kw=float(_require(profiles, "load_noise_std_kw", "simulation.profiles")),
    )
    _validate_profiles(profile_config)

    start_time_raw = str(_require(simulation, "start_time", "simulation"))
    try:
        start_time = datetime.fromisoformat(start_time_raw)
    except ValueError as exc:
        raise ConfigurationError("simulation.start_time must be an ISO-8601 timestamp") from exc
    if start_time.tzinfo is None:
        raise ConfigurationError("simulation.start_time must include a UTC offset")

    simulation_config = SimulationConfig(
        start_time=start_time,
        duration_hours=int(_require(simulation, "duration_hours", "simulation")),
        timestep_minutes=int(_require(simulation, "timestep_minutes", "simulation")),
        profiles=profile_config,
        battery=battery_config,
    )
    if simulation_config.duration_hours <= 0 or simulation_config.timestep_minutes <= 0:
        raise ConfigurationError("Simulation duration and timestep must be positive")

    detection_config = DetectionConfig(
        robust_z_threshold=float(_require(detection, "robust_z_threshold", "detection")),
        calibration_quantile=float(_require(detection, "calibration_quantile", "detection")),
        physics_min_votes=int(_require(detection, "physics_min_votes", "detection")),
        ml_score_percentile=float(_require(detection, "ml_score_percentile", "detection")),
        persistence_window=int(_require(detection, "persistence_window", "detection")),
        persistence_votes=int(_require(detection, "persistence_votes", "detection")),
        isolation_estimators=int(_require(detection, "isolation_estimators", "detection")),
    )
    _validate_detection(detection_config)

    risk_config = RiskConfig(
        confidence_weight=float(_require(risk, "confidence_weight", "risk")),
        impact_weight=float(_require(risk, "impact_weight", "risk")),
        duration_weight=float(_require(risk, "duration_weight", "risk")),
        safety_proximity_weight=float(_require(risk, "safety_proximity_weight", "risk")),
        grid_impact_reference_kw=float(_require(risk, "grid_impact_reference_kw", "risk")),
        soc_divergence_reference=float(_require(risk, "soc_divergence_reference", "risk")),
        duration_reference_steps=int(_require(risk, "duration_reference_steps", "risk")),
        medium_threshold=float(_require(risk, "medium_threshold", "risk")),
        high_threshold=float(_require(risk, "high_threshold", "risk")),
        critical_threshold=float(_require(risk, "critical_threshold", "risk")),
    )
    _validate_risk(risk_config)

    return Settings(
        project_name=str(_require(project, "name", "project")),
        random_seed=int(_require(project, "random_seed", "project")),
        simulation=simulation_config,
        detection=detection_config,
        risk=risk_config,
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


def _validate_profiles(config: ProfileConfig) -> None:
    values = (
        config.pv_peak_kw,
        config.pv_variability_fraction,
        config.load_base_kw,
        config.load_morning_peak_kw,
        config.load_evening_peak_kw,
        config.load_noise_std_kw,
    )
    if any(value < 0 for value in values):
        raise ConfigurationError("Simulation profile parameters cannot be negative")
    if config.load_base_kw <= 0:
        raise ConfigurationError("simulation.profiles.load_base_kw must be positive")


def _require_mapping(mapping: dict[str, Any], key: str, section: str) -> dict[str, Any]:
    value = _require(mapping, key, section)
    if not isinstance(value, dict):
        raise ConfigurationError(f"{section}.{key} must be a mapping")
    return value


def _validate_detection(config: DetectionConfig) -> None:
    if config.robust_z_threshold <= 0:
        raise ConfigurationError("detection.robust_z_threshold must be positive")
    if not 0 < config.calibration_quantile < 1:
        raise ConfigurationError("detection.calibration_quantile must be between 0 and 1")
    if not 0 < config.ml_score_percentile < 1:
        raise ConfigurationError("detection.ml_score_percentile must be between 0 and 1")
    if config.physics_min_votes <= 0:
        raise ConfigurationError("detection.physics_min_votes must be positive")
    if config.persistence_window <= 0:
        raise ConfigurationError("detection.persistence_window must be positive")
    if not 0 < config.persistence_votes <= config.persistence_window:
        raise ConfigurationError("detection.persistence_votes must be within the window")
    if config.isolation_estimators < 10:
        raise ConfigurationError("detection.isolation_estimators must be at least 10")


def _validate_risk(config: RiskConfig) -> None:
    weights = (
        config.confidence_weight,
        config.impact_weight,
        config.duration_weight,
        config.safety_proximity_weight,
    )
    if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
        raise ConfigurationError("risk weights must be non-negative and sum to 1")
    if (
        config.grid_impact_reference_kw <= 0
        or config.soc_divergence_reference <= 0
        or config.duration_reference_steps <= 0
    ):
        raise ConfigurationError("risk reference values must be positive")
    thresholds = (
        config.medium_threshold,
        config.high_threshold,
        config.critical_threshold,
    )
    if not 0 <= thresholds[0] < thresholds[1] < thresholds[2] <= 100:
        raise ConfigurationError("risk thresholds must increase between 0 and 100")
