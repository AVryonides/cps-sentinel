"""Detection feature contract derived from twin and command-path evidence."""

from __future__ import annotations

import pandas as pd

FEATURES = (
    "pv_residual_kw",
    "load_residual_kw",
    "battery_power_residual_kw",
    "grid_power_residual_kw",
    "battery_soc_residual",
    "measurement_balance_error_kw",
    "battery_command_residual_kw",
)

FEATURE_FLOORS = {
    "pv_residual_kw": 0.15,
    "load_residual_kw": 0.15,
    "battery_power_residual_kw": 0.15,
    "grid_power_residual_kw": 0.15,
    "battery_soc_residual": 0.005,
    "measurement_balance_error_kw": 0.15,
    "battery_command_residual_kw": 0.10,
}


def prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create detector inputs without consulting ground-truth columns."""
    enriched = frame.copy()
    enriched["battery_command_residual_kw"] = (
        enriched["commanded_battery_power_kw"] - enriched["requested_battery_power_kw"]
    )
    missing = set(FEATURES).difference(enriched.columns)
    if missing:
        raise ValueError(f"Detection frame is missing features: {sorted(missing)}")
    return enriched
