"""Physical-impact summaries for labeled scenario runs."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScenarioSummary:
    active_steps: int
    peak_pv_sensor_error_kw: float
    peak_load_sensor_error_kw: float
    peak_command_deviation_kw: float
    peak_grid_residual_kw: float
    peak_soc_residual: float
    active_action_disagreement_rate: float


def summarize_scenario(frame: pd.DataFrame) -> ScenarioSummary:
    """Summarize injected disturbance and resulting physical divergence."""
    active = frame[frame["scenario_active"]]
    if active.empty:
        raise ValueError("Scenario output does not contain an active window")
    return ScenarioSummary(
        active_steps=len(active),
        peak_pv_sensor_error_kw=float((active["pv_kw"] - active["true_pv_kw"]).abs().max()),
        peak_load_sensor_error_kw=float((active["load_kw"] - active["true_load_kw"]).abs().max()),
        peak_command_deviation_kw=float(
            (active["commanded_battery_power_kw"] - active["requested_battery_power_kw"])
            .abs()
            .max()
        ),
        peak_grid_residual_kw=float(active["grid_power_residual_kw"].abs().max()),
        peak_soc_residual=float(active["battery_soc_residual"].abs().max()),
        active_action_disagreement_rate=float((~active["controller_action_match"]).mean()),
    )
