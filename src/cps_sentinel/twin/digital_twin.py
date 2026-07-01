"""Independent model-based digital twin for the simulated nanogrid."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cps_sentinel.config import Settings
from cps_sentinel.simulation.profiles import generate_reference_profiles
from cps_sentinel.simulation.simulator import simulate_profiles

EXPECTED_NAMES = {
    "pv_kw": "expected_pv_kw",
    "load_kw": "expected_load_kw",
    "battery_soc_start": "expected_battery_soc_start",
    "battery_soc": "expected_battery_soc",
    "requested_battery_power_kw": "expected_requested_battery_power_kw",
    "battery_power_kw": "expected_battery_power_kw",
    "grid_power_kw": "expected_grid_power_kw",
    "controller_action": "expected_controller_action",
    "power_balance_error_kw": "twin_power_balance_error_kw",
    "system_state": "expected_system_state",
}


@dataclass(frozen=True)
class TwinSummary:
    rows: int
    pv_mae_kw: float
    load_mae_kw: float
    battery_power_mae_kw: float
    grid_power_mae_kw: float
    battery_soc_mae: float
    controller_action_agreement: float
    maximum_twin_balance_error_kw: float


def run_digital_twin(settings: Settings, observed: pd.DataFrame) -> pd.DataFrame:
    """Run the independent twin and append expected values and signed residuals.

    Expected values depend only on configuration, timestamp, and the twin's internal state.
    Observed sensor values are used only after prediction to calculate residuals.
    """
    _validate_observed(observed)
    reference = generate_reference_profiles(settings)
    observed_timestamps = pd.to_datetime(observed["timestamp"], utc=True)
    reference_timestamps = pd.to_datetime(reference["timestamp"], utc=True)
    if len(observed) != len(reference) or not observed_timestamps.reset_index(drop=True).equals(
        reference_timestamps.reset_index(drop=True)
    ):
        raise ValueError("Observed data must align exactly with the configured twin timeline")

    expected = simulate_profiles(settings, reference).rename(columns=EXPECTED_NAMES)
    combined = observed.reset_index(drop=True).copy()
    for column in EXPECTED_NAMES.values():
        combined[column] = expected[column].to_numpy()

    combined["pv_residual_kw"] = combined["pv_kw"] - combined["expected_pv_kw"]
    combined["load_residual_kw"] = combined["load_kw"] - combined["expected_load_kw"]
    combined["battery_power_residual_kw"] = (
        combined["battery_power_kw"] - combined["expected_battery_power_kw"]
    )
    combined["grid_power_residual_kw"] = (
        combined["grid_power_kw"] - combined["expected_grid_power_kw"]
    )
    combined["battery_soc_residual"] = combined["battery_soc"] - combined["expected_battery_soc"]
    combined["controller_action_match"] = (
        combined["controller_action"] == combined["expected_controller_action"]
    )
    return combined


def summarize_twin(frame: pd.DataFrame) -> TwinSummary:
    """Summarize normal model mismatch without classifying anomalies."""
    return TwinSummary(
        rows=len(frame),
        pv_mae_kw=float(frame["pv_residual_kw"].abs().mean()),
        load_mae_kw=float(frame["load_residual_kw"].abs().mean()),
        battery_power_mae_kw=float(frame["battery_power_residual_kw"].abs().mean()),
        grid_power_mae_kw=float(frame["grid_power_residual_kw"].abs().mean()),
        battery_soc_mae=float(frame["battery_soc_residual"].abs().mean()),
        controller_action_agreement=float(frame["controller_action_match"].mean()),
        maximum_twin_balance_error_kw=float(frame["twin_power_balance_error_kw"].abs().max()),
    )


def _validate_observed(observed: pd.DataFrame) -> None:
    required = {
        "timestamp",
        "pv_kw",
        "load_kw",
        "battery_power_kw",
        "grid_power_kw",
        "battery_soc",
        "controller_action",
    }
    missing = required.difference(observed.columns)
    if missing:
        raise ValueError(f"Observed frame is missing columns: {sorted(missing)}")
