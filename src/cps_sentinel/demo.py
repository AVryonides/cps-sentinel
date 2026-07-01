"""Reproducible local demo workflow for CPS Sentinel."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from plotly.io import write_html

from cps_sentinel.config import Settings
from cps_sentinel.dashboard import (
    DashboardResult,
    HealthDashboardResult,
    SwatDashboardResult,
    build_health_dashboard_figure,
    build_swat_dashboard_figure,
    load_health_dashboard_result,
    load_swat_dashboard_result,
    plain_language_summary,
)
from cps_sentinel.detection import (
    HybridDetector,
    aggregate_events,
    evaluate_detection,
    write_events,
)
from cps_sentinel.detection.plotting import write_detection_plot
from cps_sentinel.risk import assess_events, write_alerts
from cps_sentinel.risk.plotting import write_risk_plot
from cps_sentinel.scenarios import load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin


@dataclass(frozen=True)
class DemoArtifact:
    """One generated or referenced artifact in the local demo bundle."""

    path: str
    kind: str
    description: str


@dataclass(frozen=True)
class DemoTrackSummary:
    """Compact status and metrics for one demo track."""

    name: str
    status: str
    summary: str
    metrics: dict[str, str]
    next_step: str | None = None


@dataclass(frozen=True)
class DemoResult:
    """Outputs produced by the reproducible demo workflow."""

    output_dir: Path
    report_path: Path
    manifest_path: Path
    artifacts: tuple[DemoArtifact, ...]
    tracks: tuple[DemoTrackSummary, ...]


def run_demo_workflow(
    *,
    root: Path,
    settings: Settings,
    scenario_path: Path,
    output_dir: Path,
    health_result_path: Path,
    swat_result_path: Path,
) -> DemoResult:
    """Generate a local, reproducible demo bundle from committed code and local outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[DemoArtifact] = []
    tracks: list[DemoTrackSummary] = []

    nanogrid_track, nanogrid_artifacts = _run_nanogrid_demo(settings, scenario_path, output_dir)
    tracks.append(nanogrid_track)
    artifacts.extend(nanogrid_artifacts)

    health_track, health_artifacts = _summarize_health_track(
        settings, health_result_path, output_dir
    )
    tracks.append(health_track)
    artifacts.extend(health_artifacts)

    swat_track, swat_artifacts = _summarize_swat_track(settings, swat_result_path, output_dir)
    tracks.append(swat_track)
    artifacts.extend(swat_artifacts)

    report_path = output_dir / "demo-summary.md"
    manifest_path = output_dir / "demo-manifest.json"
    report_artifact = DemoArtifact(str(report_path), "report", "Human-readable local demo summary")
    manifest_artifact = DemoArtifact(
        str(manifest_path), "manifest", "Machine-readable demo artifact manifest"
    )
    all_artifacts = [*artifacts, report_artifact, manifest_artifact]
    _write_report(
        report_path,
        root=root,
        scenario_path=scenario_path,
        tracks=tracks,
        artifacts=all_artifacts,
    )
    manifest_path.write_text(
        json.dumps(
            {
                "scenario": str(scenario_path),
                "tracks": [asdict(track) for track in tracks],
                "artifacts": [asdict(artifact) for artifact in all_artifacts],
                "report": str(report_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return DemoResult(
        output_dir=output_dir,
        report_path=report_path,
        manifest_path=manifest_path,
        artifacts=tuple(all_artifacts),
        tracks=tuple(tracks),
    )


def _run_nanogrid_demo(
    settings: Settings, scenario_path: Path, output_dir: Path
) -> tuple[DemoTrackSummary, list[DemoArtifact]]:
    total_steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    scenario = load_scenario(scenario_path, total_steps)
    normal_twin = run_digital_twin(settings, run_simulation(settings))
    scenario_twin = run_digital_twin(settings, run_simulation(settings, scenario))
    detector = HybridDetector(settings.detection, settings.random_seed).fit(normal_twin)
    frame = detector.detect(scenario_twin)
    evaluation = evaluate_detection(frame)
    events = aggregate_events(frame)
    alerts = assess_events(frame, events, settings)
    primary_alert = alerts[0] if alerts else None

    detection_csv = output_dir / "nanogrid-detection.csv"
    events_json = output_dir / "nanogrid-events.json"
    alerts_json = output_dir / "nanogrid-alerts.json"
    detection_html = output_dir / "nanogrid-detection.html"
    risk_html = output_dir / "nanogrid-risk.html"
    frame.to_csv(detection_csv, index=False)
    write_events(events, events_json)
    write_alerts(alerts, alerts_json)
    write_detection_plot(frame, detection_html)
    write_risk_plot(frame, alerts, settings.simulation.battery, risk_html)

    dashboard_result = DashboardResult(
        scenario=scenario,
        frame=frame,
        evaluation=evaluation,
        alerts=tuple(alerts),
    )
    heading, explanation = plain_language_summary(dashboard_result)
    risk_text = f"{primary_alert.risk_score:.1f} / 100" if primary_alert else "0.0 / 100"
    summary = f"{heading}. {explanation}"
    track = DemoTrackSummary(
        name="Nanogrid attack/fault demonstrator",
        status="ready",
        summary=summary,
        metrics={
            "scenario": scenario.name,
            "precision": f"{evaluation.precision:.3f}",
            "recall": f"{evaluation.recall:.3f}",
            "f1": f"{evaluation.f1:.3f}",
            "risk_score": risk_text,
            "events": str(len(events)),
        },
    )
    artifacts = [
        DemoArtifact(str(detection_csv), "csv", "Row-level nanogrid detection output"),
        DemoArtifact(str(events_json), "json", "Aggregated nanogrid detection events"),
        DemoArtifact(str(alerts_json), "json", "Risk-ranked operator alerts"),
        DemoArtifact(str(detection_html), "html", "Interactive detection evidence report"),
        DemoArtifact(str(risk_html), "html", "Interactive risk-response report"),
    ]
    return track, artifacts


def _summarize_health_track(
    settings: Settings, health_result_path: Path, output_dir: Path
) -> tuple[DemoTrackSummary, list[DemoArtifact]]:
    state = load_health_dashboard_result(health_result_path)
    if not isinstance(state.result, HealthDashboardResult):
        return (
            DemoTrackSummary(
                name="NASA battery health validation",
                status=state.status,
                summary=state.message,
                metrics={},
                next_step=(
                    "cps-sentinel health --config config/default.yaml "
                    "--input data/raw/nasa/battery-aging-fy08q4 "
                    "--output data/processed/nasa-battery-health.csv "
                    "--alerts data/processed/nasa-health-alerts.json "
                    "--plot reports/figures/nasa-battery-health.html"
                ),
            ),
            [],
        )

    result = state.result
    figure_path = output_dir / "nasa-battery-health.html"
    write_html(build_health_dashboard_figure(result, settings), figure_path)
    critical = sum(alert.health_status == "critical" for alert in result.alerts)
    track = DemoTrackSummary(
        name="NASA battery health validation",
        status="ready",
        summary="Processed NASA battery result loaded from the local data boundary.",
        metrics={
            "batteries": str(result.frame["battery_id"].nunique()),
            "cycles": f"{len(result.frame):,}",
            "rul_mae_cycles": f"{result.evaluation.mae_cycles:.2f}",
            "critical_alerts": str(critical),
        },
    )
    return track, [DemoArtifact(str(figure_path), "html", "Interactive NASA health report")]


def _summarize_swat_track(
    settings: Settings, swat_result_path: Path, output_dir: Path
) -> tuple[DemoTrackSummary, list[DemoArtifact]]:
    state = load_swat_dashboard_result(swat_result_path, settings)
    if not isinstance(state.result, SwatDashboardResult):
        return (
            DemoTrackSummary(
                name="iTrust SWaT security validation",
                status=state.status,
                summary=state.message,
                metrics={},
                next_step=(
                    "cps-sentinel swat --config config/default.yaml --scheduled-run "
                    '"data/raw/itrust/SWaT.A4 & A5_Jul 2019/SWaT_dataset_Jul 19 v2.xlsx" '
                    "--schedule swat-a4-a5-jul-2019 "
                    "--output data/processed/swat-security.csv "
                    "--events data/processed/swat-security-events.json "
                    "--plot reports/figures/swat-security.html"
                ),
            ),
            [],
        )

    result = state.result
    figure_path = output_dir / "swat-security.html"
    write_html(build_swat_dashboard_figure(result), figure_path)
    track = DemoTrackSummary(
        name="iTrust SWaT security validation",
        status="ready",
        summary="Processed SWaT security result loaded; restricted raw historian files stay local.",
        metrics={
            "rows": f"{result.evaluation.rows:,}",
            "point_f1": f"{result.evaluation.f1:.3f}",
            "event_recall": f"{result.evaluation.event_recall:.1%}",
            "false_positive_rate": f"{result.evaluation.false_positive_rate:.2%}",
            "events": str(len(result.events)),
        },
    )
    return track, [DemoArtifact(str(figure_path), "html", "Interactive SWaT security report")]


def _write_report(
    path: Path,
    *,
    root: Path,
    scenario_path: Path,
    tracks: list[DemoTrackSummary],
    artifacts: list[DemoArtifact],
) -> None:
    lines = [
        "# CPS Sentinel reproducible demo",
        "",
        "This report was generated locally from committed code plus any processed local validation "
        "outputs already present on this machine.",
        "",
        "Raw NASA and iTrust/SWaT files are not copied, embedded, or redistributed.",
        "",
        "## Inputs",
        "",
        f"- Project root: `{root}`",
        f"- Flagship scenario: `{scenario_path}`",
        "",
        "## Track summaries",
        "",
    ]
    for track in tracks:
        lines.extend(
            [
                f"### {track.name}",
                "",
                f"- Status: `{track.status}`",
                f"- Summary: {track.summary}",
            ]
        )
        for key, value in track.metrics.items():
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        if track.next_step:
            lines.extend(
                ["", "To activate this track locally:", "", "```bash", track.next_step, "```"]
            )
        lines.append("")

    lines.extend(["## Generated artifacts", ""])
    for artifact in artifacts:
        lines.append(f"- `{artifact.path}` - {artifact.description}")
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```bash",
            "cps-sentinel demo --config config/default.yaml --output-dir reports/demo",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
