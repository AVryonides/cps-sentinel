"""Operator-facing incident report export for CPS Sentinel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cps_sentinel.config import Settings
from cps_sentinel.dashboard import DashboardResult, plain_language_summary
from cps_sentinel.detection import HybridDetector, aggregate_events, evaluate_detection
from cps_sentinel.risk import assess_events
from cps_sentinel.scenarios import load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin


@dataclass(frozen=True)
class IncidentReportResult:
    """Metadata for one generated incident report."""

    report_path: Path
    scenario_name: str
    alerts: int
    primary_risk: str


def run_incident_report(
    *,
    settings: Settings,
    scenario_path: Path,
    output_path: Path,
) -> IncidentReportResult:
    """Run the flagship pipeline and export a human-readable incident report."""
    total_steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    scenario = load_scenario(scenario_path, total_steps)
    normal_twin = run_digital_twin(settings, run_simulation(settings))
    scenario_twin = run_digital_twin(settings, run_simulation(settings, scenario))
    detector = HybridDetector(settings.detection, settings.random_seed).fit(normal_twin)
    frame = detector.detect(scenario_twin)
    evaluation = evaluate_detection(frame)
    events = aggregate_events(frame)
    alerts = assess_events(frame, events, settings)
    dashboard_result = DashboardResult(
        scenario=scenario,
        frame=frame,
        evaluation=evaluation,
        alerts=tuple(alerts),
    )
    heading, summary = plain_language_summary(dashboard_result)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _render_report(
            settings=settings,
            scenario_path=scenario_path,
            result=dashboard_result,
            heading=heading,
            summary=summary,
        ),
        encoding="utf-8",
    )
    primary = alerts[0] if alerts else None
    return IncidentReportResult(
        report_path=output_path,
        scenario_name=scenario.name,
        alerts=len(alerts),
        primary_risk=f"{primary.risk_score:.1f} / 100" if primary else "0.0 / 100",
    )


def _render_report(
    *,
    settings: Settings,
    scenario_path: Path,
    result: DashboardResult,
    heading: str,
    summary: str,
) -> str:
    alert = result.primary_alert
    evaluation = result.evaluation
    lines = [
        "# CPS Sentinel operator incident report",
        "",
        "This report was generated locally from committed CPS Sentinel code. It is intended as "
        "operator decision support and reproducible incident evidence, not as an autonomous "
        "control log.",
        "",
        "## Executive summary",
        "",
        f"**{heading}.** {summary}",
        "",
        "## Scenario and reproducibility",
        "",
        f"- Project: `{settings.project_name}`",
        f"- Scenario file: `{scenario_path}`",
        f"- Scenario name: {result.scenario.name}",
        f"- Scenario type: {result.scenario.kind.value.replace('_', ' ')}",
        f"- Target: {result.scenario.target.value}",
        f"- Ground-truth label: {result.scenario.ground_truth_label}",
        f"- Random seed: `{settings.random_seed}`",
        "",
        "## Detection outcome",
        "",
        f"- Precision: {evaluation.precision:.3f}",
        f"- Recall: {evaluation.recall:.3f}",
        f"- F1 score: {evaluation.f1:.3f}",
        f"- False-positive rate: {evaluation.false_positive_rate:.3f}",
        f"- Event detected: {evaluation.event_detected}",
        f"- Detection delay: {evaluation.detection_delay_steps} step(s)",
        f"- Aggregated alerts: {len(result.alerts)}",
        "",
    ]
    if alert is None:
        lines.extend(
            [
                "## Primary alert",
                "",
                "No persistent event was detected, so no operator response sequence was produced.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Primary alert",
                "",
                f"- Alert ID: `{alert.alert_id}`",
                f"- Time window: {alert.start_time} to {alert.end_time}",
                f"- Risk level: **{alert.risk_level.upper()}**",
                f"- Risk score: **{alert.risk_score:.1f} / 100**",
                f"- Likely event: `{alert.likely_event}`",
                f"- Affected component: `{alert.affected_component}`",
                f"- Confidence: {alert.confidence:.3f}",
                f"- Physical impact: {alert.physical_impact}",
                "",
                "## Evidence",
                "",
            ]
        )
        for item in alert.evidence:
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "## Risk factor breakdown",
                "",
                "| Factor | Value |",
                "| --- | ---: |",
                f"| Confidence | {alert.confidence_factor:.3f} |",
                f"| Physical impact | {alert.impact_factor:.3f} |",
                f"| Duration | {alert.duration_factor:.3f} |",
                f"| Safety proximity | {alert.safety_proximity_factor:.3f} |",
                "",
                "## Recommended operator sequence",
                "",
            ]
        )
        for index, action in enumerate(alert.recommended_actions, start=1):
            lines.append(f"{index}. {action}")
        lines.extend(["", "## Safety boundary", "", alert.safety_note, ""])

    lines.extend(
        [
            "## Re-run command",
            "",
            "```bash",
            "cps-sentinel report \\",
            "  --config config/default.yaml \\",
            f"  --scenario {scenario_path} \\",
            "  --output reports/incidents/nanogrid-incident-report.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)
