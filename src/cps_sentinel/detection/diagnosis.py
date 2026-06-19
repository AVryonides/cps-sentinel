"""Explainable rule-based diagnosis from detector evidence."""

from __future__ import annotations

import pandas as pd


def diagnose_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Assign coarse likely event and affected component without using ground truth."""
    diagnosed = frame.copy()
    diagnoses = [
        _diagnose_row(bool(row.detected), str(row.physics_evidence))
        for row in diagnosed.itertuples(index=False)
    ]
    diagnosed["likely_event"] = [item[0] for item in diagnoses]
    diagnosed["affected_component"] = [item[1] for item in diagnoses]
    diagnosed["diagnosis_rationale"] = [item[2] for item in diagnoses]
    return diagnosed


def _diagnose_row(detected: bool, evidence: str) -> tuple[str, str, str]:
    if not detected:
        return "normal", "none", "No persistent hybrid anomaly"
    feature_set = set(filter(None, evidence.split("|")))
    if "battery_command_residual_kw" in feature_set:
        return (
            "battery_command_integrity_event",
            "battery_command_path",
            "Delivered battery command diverges from the controller request",
        )
    if "pv_residual_kw" in feature_set or "measurement_balance_error_kw" in feature_set:
        return (
            "pv_sensor_integrity_event",
            "pv_sensor",
            "PV/twin divergence or sensor-based power imbalance is persistent",
        )
    if "load_residual_kw" in feature_set:
        return (
            "load_sensor_integrity_event",
            "load_sensor",
            "Reported load diverges persistently from the independent expectation",
        )
    if "battery_soc_residual" in feature_set:
        return (
            "battery_state_divergence",
            "battery",
            "Observed battery state diverges from the physics-based twin",
        )
    if {"battery_power_residual_kw", "grid_power_residual_kw"} & feature_set:
        return (
            "power_flow_anomaly",
            "nanogrid_power_flow",
            "Battery/grid power differs persistently from expected operation",
        )
    return (
        "multivariate_cps_anomaly",
        "unknown",
        "The statistical detector found an unusual residual combination",
    )
