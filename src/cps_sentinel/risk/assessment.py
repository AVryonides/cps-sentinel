"""Translate detected CPS events into risk-ranked operator alerts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from cps_sentinel.config import Settings
from cps_sentinel.detection.events import EventRecord

SAFETY_NOTE = (
    "Advisory only: recommendations are bounded and reversible. "
    "A qualified operator must confirm any control action."
)


@dataclass(frozen=True)
class AlertRecord:
    """Prioritized, explainable decision-support record for one detected event."""

    alert_id: str
    priority: int
    event_id: int
    start_time: str
    end_time: str
    likely_event: str
    affected_component: str
    confidence: float
    risk_score: float
    risk_level: str
    physical_impact: str
    peak_grid_residual_kw: float
    peak_soc_residual: float
    peak_command_deviation_kw: float
    minimum_soc_safety_margin: float
    confidence_factor: float
    impact_factor: float
    duration_factor: float
    safety_proximity_factor: float
    evidence: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    safety_note: str = SAFETY_NOTE


def assess_events(
    frame: pd.DataFrame, events: list[EventRecord], settings: Settings
) -> list[AlertRecord]:
    """Score physical consequence and produce highest-risk-first alerts."""
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    provisional: list[AlertRecord] = []
    battery = settings.simulation.battery
    risk = settings.risk

    for event in events:
        start = pd.to_datetime(event.start_time, utc=True)
        end = pd.to_datetime(event.end_time, utc=True)
        rows = frame.loc[(timestamps >= start) & (timestamps <= end)]
        if rows.empty:
            raise ValueError(f"No frame rows found for event {event.event_id}")

        peak_grid = _peak_absolute(rows, "grid_power_residual_kw")
        peak_soc = _peak_absolute(rows, "battery_soc_residual")
        peak_command = _peak_absolute(rows, "battery_command_residual_kw")
        peak_balance = _peak_absolute(rows, "measurement_balance_error_kw")
        soc_margin = _minimum_soc_margin(rows, battery.minimum_soc, battery.maximum_soc)

        confidence_factor = _bound(event.confidence)
        impact_factor = max(
            _bound(peak_grid / risk.grid_impact_reference_kw),
            _bound(peak_balance / risk.grid_impact_reference_kw),
            _bound(peak_soc / risk.soc_divergence_reference),
            _bound(peak_command / battery.maximum_power_kw),
        )
        duration_factor = _bound(event.duration_steps / risk.duration_reference_steps)
        half_soc_window = (battery.maximum_soc - battery.minimum_soc) / 2
        safety_factor = _bound(1 - soc_margin / half_soc_window)
        score = 100 * (
            risk.confidence_weight * confidence_factor
            + risk.impact_weight * impact_factor
            + risk.duration_weight * duration_factor
            + risk.safety_proximity_weight * safety_factor
        )
        score = round(float(np.clip(score, 0, 100)), 1)

        provisional.append(
            AlertRecord(
                alert_id=f"ALT-{event.event_id:04d}",
                priority=0,
                event_id=event.event_id,
                start_time=event.start_time,
                end_time=event.end_time,
                likely_event=event.likely_event,
                affected_component=event.affected_component,
                confidence=round(event.confidence, 3),
                risk_score=score,
                risk_level=_risk_level(score, settings),
                physical_impact=_impact_summary(
                    peak_grid, peak_soc, peak_command, peak_balance, soc_margin
                ),
                peak_grid_residual_kw=round(peak_grid, 4),
                peak_soc_residual=round(peak_soc, 5),
                peak_command_deviation_kw=round(peak_command, 4),
                minimum_soc_safety_margin=round(soc_margin, 5),
                confidence_factor=round(confidence_factor, 3),
                impact_factor=round(impact_factor, 3),
                duration_factor=round(duration_factor, 3),
                safety_proximity_factor=round(safety_factor, 3),
                evidence=event.evidence,
                recommended_actions=_recommendations(event.likely_event),
            )
        )

    ranked = sorted(provisional, key=lambda alert: (-alert.risk_score, alert.event_id))
    return [
        AlertRecord(**{**asdict(alert), "priority": priority})
        for priority, alert in enumerate(ranked, start=1)
    ]


def write_alerts(alerts: list[AlertRecord], path: str | Path) -> Path:
    """Write risk-ranked alerts as human-readable JSON."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([asdict(alert) for alert in alerts], indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def _peak_absolute(rows: pd.DataFrame, column: str) -> float:
    return float(rows[column].abs().max()) if column in rows else 0.0


def _minimum_soc_margin(rows: pd.DataFrame, minimum: float, maximum: float) -> float:
    soc = rows["battery_soc"].astype(float)
    return max(0.0, float(np.minimum(soc - minimum, maximum - soc).min()))


def _bound(value: float) -> float:
    return float(np.clip(value, 0, 1))


def _risk_level(score: float, settings: Settings) -> str:
    thresholds = settings.risk
    if score >= thresholds.critical_threshold:
        return "critical"
    if score >= thresholds.high_threshold:
        return "high"
    if score >= thresholds.medium_threshold:
        return "medium"
    return "low"


def _impact_summary(grid: float, soc: float, command: float, balance: float, margin: float) -> str:
    return (
        f"Peak grid-flow divergence {grid:.2f} kW; SOC divergence {soc:.3f}; "
        f"command deviation {command:.2f} kW; sensor-balance error {balance:.2f} kW. "
        f"Closest observed SOC remained {margin:.3f} from a configured safety limit."
    )


def _recommendations(likely_event: str) -> tuple[str, ...]:
    common = "Require operator confirmation before restoring normal automatic control."
    policies: dict[str, tuple[str, ...]] = {
        "pv_sensor_integrity_event": (
            "Mark PV telemetry untrusted and exclude it from automatic control decisions.",
            "Use the bounded digital-twin PV estimate while cross-checking inverter telemetry.",
            "Inspect timestamp, calibration, and communication integrity for the PV sensor.",
            common,
        ),
        "load_sensor_integrity_event": (
            "Mark load telemetry untrusted and exclude it from automatic control decisions.",
            "Use a bounded twin estimate and independently verify feeder measurements.",
            common,
        ),
        "battery_command_integrity_event": (
            "Block the suspect command path and hold a bounded last-verified battery setpoint.",
            "Verify controller-to-actuator authentication, ordering, and command timestamps.",
            "Keep battery power and SOC within configured limits during investigation.",
            common,
        ),
        "battery_state_divergence": (
            "Reduce battery charge/discharge limits and maintain grid-supported operation.",
            "Inspect battery telemetry, efficiency, temperature, and state estimator health.",
            common,
        ),
        "power_flow_anomaly": (
            "Select conservative grid-connected operation with bounded battery power.",
            "Cross-check meter, inverter, and breaker states before changing dispatch.",
            common,
        ),
    }
    return policies.get(
        likely_event,
        (
            "Escalate for manual review and preserve relevant telemetry and command logs.",
            "Maintain conservative bounded operation until the anomaly is explained.",
            common,
        ),
    )
