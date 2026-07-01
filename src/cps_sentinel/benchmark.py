"""Scenario benchmark matrix for CPS Sentinel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from cps_sentinel.config import Settings
from cps_sentinel.detection import HybridDetector, aggregate_events, evaluate_detection
from cps_sentinel.risk import assess_events
from cps_sentinel.scenarios import load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin


@dataclass(frozen=True)
class ScenarioBenchmarkRow:
    """One row in the committed-code scenario benchmark matrix."""

    scenario: str
    scenario_file: str
    kind: str
    target: str
    label: str
    active_steps: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    event_detected: bool
    detection_delay_steps: int | None
    alerts: int
    top_risk_score: float
    top_risk_level: str
    likely_event: str
    affected_component: str


@dataclass(frozen=True)
class ScenarioBenchmarkResult:
    """Outputs and summary for a scenario benchmark run."""

    rows: tuple[ScenarioBenchmarkRow, ...]
    csv_path: Path
    report_path: Path

    @property
    def average_f1(self) -> float:
        return sum(row.f1 for row in self.rows) / len(self.rows) if self.rows else 0.0

    @property
    def detected_events(self) -> int:
        return sum(1 for row in self.rows if row.event_detected)


def run_scenario_benchmark(
    *,
    settings: Settings,
    scenario_dir: Path,
    output_csv: Path,
    output_report: Path,
) -> ScenarioBenchmarkResult:
    """Evaluate every scenario YAML with one clean baseline detector calibration."""
    scenario_paths = tuple(sorted(scenario_dir.glob("*.yaml")))
    if not scenario_paths:
        raise ValueError(f"No scenario YAML files found under {scenario_dir}")

    total_steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    normal_twin = run_digital_twin(settings, run_simulation(settings))
    detector = HybridDetector(settings.detection, settings.random_seed).fit(normal_twin)
    rows = tuple(
        _evaluate_scenario(settings, detector, path, total_steps) for path in scenario_paths
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(row) for row in rows]).to_csv(output_csv, index=False)
    output_report.write_text(_render_report(rows, scenario_dir), encoding="utf-8")
    return ScenarioBenchmarkResult(rows=rows, csv_path=output_csv, report_path=output_report)


def _evaluate_scenario(
    settings: Settings,
    detector: HybridDetector,
    scenario_path: Path,
    total_steps: int,
) -> ScenarioBenchmarkRow:
    scenario = load_scenario(scenario_path, total_steps)
    frame = detector.detect(run_digital_twin(settings, run_simulation(settings, scenario)))
    evaluation = evaluate_detection(frame)
    events = aggregate_events(frame)
    alerts = assess_events(frame, events, settings)
    primary = alerts[0] if alerts else None
    return ScenarioBenchmarkRow(
        scenario=scenario.name,
        scenario_file=str(scenario_path),
        kind=scenario.kind.value,
        target=scenario.target.value,
        label=scenario.ground_truth_label,
        active_steps=int(frame["scenario_active"].sum()),
        precision=round(evaluation.precision, 3),
        recall=round(evaluation.recall, 3),
        f1=round(evaluation.f1, 3),
        false_positive_rate=round(evaluation.false_positive_rate, 3),
        event_detected=evaluation.event_detected,
        detection_delay_steps=evaluation.detection_delay_steps,
        alerts=len(alerts),
        top_risk_score=primary.risk_score if primary else 0.0,
        top_risk_level=primary.risk_level if primary else "none",
        likely_event=primary.likely_event if primary else "none",
        affected_component=primary.affected_component if primary else "none",
    )


def _render_report(rows: tuple[ScenarioBenchmarkRow, ...], scenario_dir: Path) -> str:
    detected = sum(1 for row in rows if row.event_detected)
    average_f1 = sum(row.f1 for row in rows) / len(rows)
    average_risk = sum(row.top_risk_score for row in rows) / len(rows)
    lines = [
        "# CPS Sentinel scenario benchmark matrix",
        "",
        "This report evaluates every committed nanogrid scenario with one detector calibrated "
        "only on clean baseline behavior.",
        "",
        "## Summary",
        "",
        f"- Scenario directory: `{scenario_dir}`",
        f"- Scenarios evaluated: {len(rows)}",
        f"- Events detected: {detected}/{len(rows)}",
        f"- Average F1: {average_f1:.3f}",
        f"- Average top risk score: {average_risk:.1f} / 100",
        "",
        "## Matrix",
        "",
        "| Scenario | Label | Target | F1 | Delay | Risk | Diagnosis |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        delay = "n/a" if row.detection_delay_steps is None else str(row.detection_delay_steps)
        lines.append(
            f"| {row.scenario} | {row.label} | {row.target} | {row.f1:.3f} | "
            f"{delay} | {row.top_risk_score:.1f} | {row.likely_event} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The benchmark is intended to show coverage across scenario families, not to replace "
            "the detailed interactive dashboard or operator incident report. Labels are used only "
            "after detection for evaluation.",
            "",
            "## Re-run command",
            "",
            "```bash",
            "cps-sentinel benchmark \\",
            "  --config config/default.yaml \\",
            "  --scenario-dir config/scenarios \\",
            "  --output reports/benchmarks/scenario-benchmark.csv \\",
            "  --report reports/benchmarks/scenario-benchmark.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)
