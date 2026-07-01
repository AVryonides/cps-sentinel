"""Causal battery state-of-health and remaining-useful-life baseline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from cps_sentinel.config import HealthConfig


@dataclass(frozen=True)
class RulEvaluation:
    evaluated_predictions: int
    mae_cycles: float
    rmse_cycles: float


@dataclass(frozen=True)
class HealthAlert:
    alert_id: str
    battery_id: str
    cycle_index: int
    health_status: str
    capacity_ah: float
    state_of_health: float
    estimated_rul_cycles: float | None
    degradation_rate_ah_per_cycle: float | None
    physical_impact: str
    recommended_actions: tuple[str, ...]
    safety_note: str = (
        "Prognostic estimate only: inspect uncertainty and confirm maintenance decisions "
        "with qualified battery personnel."
    )


def analyze_battery_health(frame: pd.DataFrame, config: HealthConfig) -> pd.DataFrame:
    """Add causal SOH, EOL, degradation-rate, and RUL estimates per battery."""
    required = {"battery_id", "cycle_index", "capacity_ah"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Battery health frame is missing columns: {sorted(missing)}")
    analyzed: list[pd.DataFrame] = []
    for _, battery_rows in frame.groupby("battery_id", sort=True):
        battery = battery_rows.sort_values("cycle_index").reset_index(drop=True).copy()
        battery["state_of_health"] = battery["capacity_ah"] / config.rated_capacity_ah
        battery["health_status"] = battery["state_of_health"].map(
            lambda soh: _health_status(float(soh), config)
        )
        eol_rows = battery.loc[battery["capacity_ah"] <= config.end_of_life_capacity_ah]
        eol_cycle = float(eol_rows["cycle_index"].iloc[0]) if not eol_rows.empty else np.nan
        battery["observed_eol_cycle"] = eol_cycle
        battery["actual_rul_cycles"] = (
            np.maximum(eol_cycle - battery["cycle_index"], 0) if np.isfinite(eol_cycle) else np.nan
        )
        estimates = [
            _causal_projection(battery.iloc[: index + 1], config) for index in range(len(battery))
        ]
        battery["estimated_rul_cycles"] = [estimate[0] for estimate in estimates]
        battery["degradation_rate_ah_per_cycle"] = [estimate[1] for estimate in estimates]
        analyzed.append(battery)
    return pd.concat(analyzed, ignore_index=True)


def evaluate_rul(frame: pd.DataFrame) -> RulEvaluation:
    """Evaluate causal RUL estimates only where an observed EOL target exists."""
    valid = frame.dropna(subset=["estimated_rul_cycles", "actual_rul_cycles"])
    if valid.empty:
        return RulEvaluation(0, float("nan"), float("nan"))
    error = valid["estimated_rul_cycles"] - valid["actual_rul_cycles"]
    return RulEvaluation(
        evaluated_predictions=len(valid),
        mae_cycles=float(error.abs().mean()),
        rmse_cycles=float(np.sqrt(np.mean(np.square(error)))),
    )


def build_health_alerts(frame: pd.DataFrame) -> list[HealthAlert]:
    """Build one latest-state health alert per battery."""
    alerts: list[HealthAlert] = []
    for battery_id, rows in frame.groupby("battery_id", sort=True):
        latest = rows.sort_values("cycle_index").iloc[-1]
        estimate = latest["estimated_rul_cycles"]
        rate = latest["degradation_rate_ah_per_cycle"]
        alerts.append(
            HealthAlert(
                alert_id=f"HLT-{battery_id}",
                battery_id=str(battery_id),
                cycle_index=int(latest["cycle_index"]),
                health_status=str(latest["health_status"]),
                capacity_ah=round(float(latest["capacity_ah"]), 4),
                state_of_health=round(float(latest["state_of_health"]), 4),
                estimated_rul_cycles=(round(float(estimate), 1) if pd.notna(estimate) else None),
                degradation_rate_ah_per_cycle=(round(float(rate), 6) if pd.notna(rate) else None),
                physical_impact=(
                    f"Measured discharge capacity is {float(latest['capacity_ah']):.3f} Ah "
                    f"({float(latest['state_of_health']):.1%} of rated capacity)."
                ),
                recommended_actions=_health_actions(str(latest["health_status"])),
            )
        )
    rank = {"critical": 0, "warning": 1, "healthy": 2}
    return sorted(alerts, key=lambda alert: (rank.get(alert.health_status, 3), alert.battery_id))


def write_health_alerts(alerts: list[HealthAlert], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([asdict(alert) for alert in alerts], indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def _causal_projection(rows: pd.DataFrame, config: HealthConfig) -> tuple[float, float]:
    if len(rows) < config.minimum_regression_cycles:
        return np.nan, np.nan
    window = rows.tail(config.regression_window_cycles)
    cycle = window["cycle_index"].to_numpy(dtype=float)
    capacity = window["capacity_ah"].to_numpy(dtype=float)
    slope, _ = np.polyfit(cycle, capacity, 1)
    current_cycle = float(rows["cycle_index"].iloc[-1])
    current_capacity = float(rows["capacity_ah"].iloc[-1])
    local_rate = max(0.0, -float(slope))
    cumulative_rate = max(0.0, (config.rated_capacity_ah - current_capacity) / current_cycle)
    degradation_rate = max(local_rate, cumulative_rate)
    if degradation_rate <= 1e-6:
        return np.nan, degradation_rate
    estimated_rul = (current_capacity - config.end_of_life_capacity_ah) / degradation_rate
    return max(0.0, estimated_rul), degradation_rate


def _health_status(soh: float, config: HealthConfig) -> str:
    if soh <= config.critical_soh_fraction:
        return "critical"
    if soh <= config.warning_soh_fraction:
        return "warning"
    return "healthy"


def _health_actions(status: str) -> tuple[str, ...]:
    if status == "critical":
        return (
            "Remove the battery from safety-critical duty and schedule replacement assessment.",
            "Verify capacity with a controlled reference discharge before maintenance action.",
            "Review temperature and impedance history for corroborating degradation evidence.",
        )
    if status == "warning":
        return (
            "Increase reference-capacity test frequency and track forecast uncertainty.",
            "Reduce reliance on the battery for high-power or low-reserve operation.",
        )
    return ("Continue scheduled monitoring and preserve the capacity trend baseline.",)
