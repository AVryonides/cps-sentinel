"""NiceGUI presentation layer for the unified CPS Sentinel operations interface."""

# ruff: noqa: E501

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nicegui import events, run, ui

from cps_sentinel.config import load_settings
from cps_sentinel.dashboard import (
    DashboardResult,
    ExternalTrackState,
    HealthDashboardResult,
    SwatDashboardResult,
    build_consequence_figure,
    build_detection_figure,
    build_health_dashboard_figure,
    build_sensor_figure,
    build_swat_dashboard_figure,
    load_health_dashboard_result,
    load_swat_dashboard_result,
    plain_language_summary,
    run_dashboard_scenario,
    scenario_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default.yaml"
SETTINGS = load_settings(CONFIG_PATH)
CATALOG = scenario_catalog(ROOT, SETTINGS)
DEFAULT_SCENARIO = next(iter(CATALOG))
HEALTH_RESULT_PATH = ROOT / "data" / "processed" / "nasa-battery-health.csv"
SWAT_RESULT_PATH = ROOT / "data" / "processed" / "swat-security.csv"
FAVICON = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="8" fill="#101720"/>
  <text x="32" y="39" text-anchor="middle" font-family="Arial" font-size="22"
        font-weight="700" fill="#42c6d7">CS</text>
</svg>
"""

CSS = """
:root {
  --bg: #090e14;
  --surface: #101720;
  --surface-raised: #151e29;
  --line: #263241;
  --line-strong: #344457;
  --text: #edf2f7;
  --muted: #94a3b3;
  --cyan: #42c6d7;
  --amber: #e5a93d;
  --red: #e66565;
}
html { scroll-behavior: smooth; background: var(--bg); }
body, .q-page, .q-layout { background: var(--bg) !important; color: var(--text); }
body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif; }
.q-drawer { background: #0c121a !important; border-right: 1px solid var(--line) !important; }
.q-header { background: rgba(9, 14, 20, .94) !important; border-bottom: 1px solid var(--line); }
.page-shell { width: min(1500px, calc(100vw - 330px)); margin: 0 auto; padding: 84px 36px 64px; }
.brand-mark { width: 38px; height: 38px; border: 1px solid var(--cyan); color: var(--cyan);
  display: grid; place-items: center; font: 700 13px/1 ui-monospace, SFMono-Regular, monospace;
  letter-spacing: .08em; }
.brand-name { color: var(--text); font-size: 15px; font-weight: 650; letter-spacing: .01em; }
.brand-sub { color: var(--muted); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }
.nav-label { color: #647485; font: 650 10px/1 ui-monospace, SFMono-Regular, monospace;
  letter-spacing: .14em; text-transform: uppercase; margin: 26px 14px 10px; }
.nav-button { width: 100%; justify-content: flex-start; color: #b7c2ce !important;
  border-left: 2px solid transparent; border-radius: 0 !important; padding: 11px 14px !important; }
.nav-button:hover { color: var(--text) !important; background: #131c26 !important;
  border-left-color: var(--cyan); }
.mode-button { width: 100%; justify-content: flex-start; color: var(--text) !important;
  border: 1px solid var(--line) !important; border-radius: 3px !important; margin-top: 7px; }
.mode-button:hover { border-color: var(--cyan) !important; background: #131c26 !important; }
.scenario-select .q-field__control { background: var(--surface); border-radius: 4px; color: var(--text); }
.scenario-select .q-field__native, .scenario-select .q-field__label,
.scenario-select .q-field__marginal { color: var(--text) !important; }
.eyebrow { color: var(--cyan); font: 650 11px/1 ui-monospace, SFMono-Regular, monospace;
  letter-spacing: .16em; text-transform: uppercase; }
.hero-title { font-size: clamp(32px, 4vw, 58px); font-weight: 620; letter-spacing: -.035em;
  line-height: 1.05; color: var(--text); max-width: 900px; margin-top: 14px; }
.hero-copy { color: #aab6c3; font-size: 17px; line-height: 1.65; max-width: 780px; margin-top: 18px; }
.status-line { border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
  padding: 15px 0; margin-top: 30px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red);
  box-shadow: 0 0 0 5px rgba(230,101,101,.11); }
.status-text { color: var(--muted); font: 600 11px/1 ui-monospace, SFMono-Regular, monospace;
  letter-spacing: .09em; text-transform: uppercase; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px;
  background: var(--line); border: 1px solid var(--line); margin-top: 28px; width: 100%; }
.metric { background: var(--surface); padding: 20px 22px; min-height: 112px; }
.metric-label { color: var(--muted); font: 600 10px/1.2 ui-monospace, SFMono-Regular, monospace;
  letter-spacing: .1em; text-transform: uppercase; }
.metric-value { color: var(--text); font-size: 25px; font-weight: 590; margin-top: 13px; }
.metric-note { color: #6f7e8d; font-size: 12px; margin-top: 7px; }
.section { scroll-margin-top: 78px; padding-top: 76px; width: 100%; }
.section-index { color: var(--cyan); font: 600 11px/1 ui-monospace, SFMono-Regular, monospace; }
.section-title { color: var(--text); font-size: 28px; font-weight: 610; letter-spacing: -.02em; }
.section-copy { color: var(--muted); font-size: 15px; line-height: 1.6; max-width: 780px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 5px;
  padding: 24px; width: 100%; }
.finding { background: #111a22; border-left: 3px solid var(--amber); padding: 26px 28px; width: 100%; }
.finding-title { color: var(--text); font-size: 23px; font-weight: 600; }
.finding-copy { color: #b4bfca; font-size: 15px; line-height: 1.7; max-width: 940px; margin-top: 10px; }
.guide { background: #0d141c; border: 1px solid var(--line); padding: 16px 18px; width: 100%; }
.guide-title { color: var(--text); font-size: 13px; font-weight: 650; }
.guide-copy { color: var(--muted); font-size: 13px; line-height: 1.55; }
.chart-wrap { background: var(--surface); border: 1px solid var(--line); padding: 8px; width: 100%; }
.risk-box { background: var(--surface); border: 1px solid var(--line); padding: 28px; width: 100%; }
.risk-score { font: 620 52px/1 ui-monospace, SFMono-Regular, monospace; color: var(--red); }
.risk-level { color: var(--red); font: 650 11px/1 ui-monospace, SFMono-Regular, monospace;
  letter-spacing: .12em; text-transform: uppercase; }
.action-row { display: grid; grid-template-columns: 36px 1fr; gap: 14px; border-top: 1px solid var(--line);
  padding: 17px 0; width: 100%; }
.action-number { color: var(--cyan); font: 600 12px/1.5 ui-monospace, SFMono-Regular, monospace; }
.action-copy { color: #c4ced8; font-size: 14px; line-height: 1.55; }
.safety-note { background: rgba(229,169,61,.07); border: 1px solid rgba(229,169,61,.28);
  color: #d9c18f; padding: 16px 18px; font-size: 13px; line-height: 1.55; width: 100%; }
.empty-state { background: var(--surface); border: 1px dashed var(--line-strong); padding: 32px;
  width: 100%; }
.track-ready { color: var(--cyan); }
.track-pending { color: var(--amber); }
.glossary-row { display: grid; grid-template-columns: 180px 1fr; gap: 24px;
  padding: 14px 0; border-top: 1px solid var(--line); }
.glossary-term { color: var(--text); font: 600 12px/1.5 ui-monospace, SFMono-Regular, monospace; }
.glossary-definition { color: var(--muted); font-size: 13px; line-height: 1.55; }
.mobile-menu { display: none !important; color: var(--text) !important; }
.footer { border-top: 1px solid var(--line); color: #667585; margin-top: 78px;
  padding-top: 22px; font-size: 12px; width: 100%; }
@media (max-width: 1050px) {
  .page-shell { width: 100%; padding: 82px 24px 52px; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .mobile-menu { display: inline-flex !important; }
}
@media (max-width: 640px) {
  .page-shell { padding: 76px 16px 40px; }
  .metric-grid { grid-template-columns: 1fr; }
  .hero-title { font-size: 34px; }
  .panel, .risk-box { padding: 18px; }
  .glossary-row { grid-template-columns: 1fr; gap: 5px; }
}
"""


def _jump_to(section_id: str) -> None:
    ui.run_javascript(
        f"document.getElementById('{section_id}')?.scrollIntoView({{behavior:'smooth'}})"
    )


def _metric(label: str, value: str, note: str) -> None:
    with ui.column().classes("metric gap-0"):
        ui.label(label).classes("metric-label")
        ui.label(value).classes("metric-value")
        ui.label(note).classes("metric-note")


def _section_heading(index: str, title: str, copy: str) -> None:
    with ui.column().classes("gap-3"):
        ui.label(index).classes("section-index")
        ui.label(title).classes("section-title")
        ui.label(copy).classes("section-copy")


def _reading_guide(title: str, copy: str) -> None:
    with ui.column().classes("guide gap-2"):
        ui.label(title).classes("guide-title")
        ui.label(copy).classes("guide-copy")


def _render_dashboard(result: DashboardResult) -> None:
    alert = result.primary_alert
    heading, summary = plain_language_summary(result)

    with ui.column().classes("w-full gap-0"):
        with ui.column().classes("w-full gap-0"):
            ui.label("CYBER-PHYSICAL SYSTEM MONITOR").classes("eyebrow")
            ui.label("Understand what happened, why it matters, and what to do next.").classes(
                "hero-title"
            )
            ui.label(
                "CPS Sentinel compares a simulated nanogrid with an independent digital twin. "
                "When the two disagree persistently, it explains the evidence in operational terms."
            ).classes("hero-copy")
            with ui.row().classes("status-line items-center gap-4 w-full"):
                ui.element("span").classes("status-dot")
                ui.label("Active event detected" if alert else "System operating normally").classes(
                    "status-text"
                )
                ui.space()
                ui.label(result.scenario.name).classes("status-text")

        with ui.element("div").classes("metric-grid"):
            _metric("System state", "Alert" if alert else "Normal", "Persistent event status")
            _metric(
                "Risk score",
                f"{alert.risk_score:.1f} / 100" if alert else "0.0 / 100",
                alert.risk_level.title() if alert else "Low",
            )
            _metric(
                "Affected component",
                alert.affected_component.replace("_", " ").title() if alert else "None",
                "Most likely source",
            )
            delay = result.evaluation.detection_delay_steps
            _metric(
                "Detection delay",
                f"{delay} step{'s' if delay != 1 else ''}",
                f"{(delay or 0) * SETTINGS.simulation.timestep_minutes} minutes",
            )

        with ui.column().classes("section gap-6").props("id=overview"):
            _section_heading(
                "01 / INCIDENT OVERVIEW",
                "What happened?",
                "Start here. This is the event translated from residuals and model scores into "
                "plain operational language.",
            )
            with ui.column().classes("finding gap-0"):
                ui.label(heading).classes("finding-title")
                ui.label(summary).classes("finding-copy")
            with ui.row().classes("w-full gap-4"):
                with ui.column().classes("panel gap-3 grow"):
                    ui.label("Scenario").classes("metric-label")
                    ui.label(result.scenario.name).classes("text-xl text-white")
                    ui.label(
                        f"{result.scenario.ground_truth_label.title()} · "
                        f"{result.scenario.kind.value.replace('_', ' ')}"
                    ).classes("guide-copy")
                with ui.column().classes("panel gap-3 grow"):
                    ui.label("Detection quality").classes("metric-label")
                    ui.label(f"F1 {result.evaluation.f1:.3f}").classes("text-xl text-white")
                    ui.label(
                        f"Precision {result.evaluation.precision:.3f} · "
                        f"Recall {result.evaluation.recall:.3f}"
                    ).classes("guide-copy")

        with ui.column().classes("section gap-6").props("id=sensor"):
            _section_heading(
                "02 / SENSOR EVIDENCE",
                "Did the sensor tell the truth?",
                "Three lines represent physical reality, the value trusted by the controller, "
                "and the independent digital-twin estimate.",
            )
            _reading_guide(
                "How to read this chart",
                "Before the shaded event window, the lines should overlap. A sustained separation "
                "of the amber reported value means the controller is seeing a different world from "
                "the physical plant and the twin.",
            )
            with ui.element("div").classes("chart-wrap"):
                ui.plotly(build_sensor_figure(result)).classes("w-full")

        with ui.column().classes("section gap-6").props("id=impact"):
            _section_heading(
                "03 / PHYSICAL CONSEQUENCE",
                "What changed in the nanogrid?",
                "A cyber event matters only when it can influence physical operation. These charts "
                "show grid exchange and battery state against their expected trajectories.",
            )
            _reading_guide(
                "Positive, negative, and safe limits",
                "Positive grid power means importing electricity; negative means exporting. Battery "
                "SOC is the stored-energy fraction. Red dotted lines are configured operating limits, "
                "not anomaly thresholds.",
            )
            with ui.element("div").classes("chart-wrap"):
                ui.plotly(build_consequence_figure(result, SETTINGS)).classes("w-full")

        with ui.column().classes("section gap-6").props("id=detection"):
            _section_heading(
                "04 / DETECTION LOGIC",
                "Why was an alert raised?",
                "The detector looks for sustained differences between observation and expectation. "
                "It combines physics-based checks with statistical novelty and temporal persistence.",
            )
            _reading_guide(
                "Residual does not mean failure",
                "A residual is simply observed minus expected. Small differences are normal. CPS "
                "Sentinel raises an event only when evidence becomes unusually large and persists "
                "across consecutive samples.",
            )
            with ui.element("div").classes("chart-wrap"):
                ui.plotly(build_detection_figure(result)).classes("w-full")

        with ui.column().classes("section gap-6").props("id=response"):
            _section_heading(
                "05 / OPERATOR RESPONSE",
                "What should happen next?",
                "Recommendations are conservative decision support. The application never sends "
                "commands to the simulated plant and never bypasses operator confirmation.",
            )
            if alert:
                with ui.column().classes("risk-box gap-5"):
                    ui.label(f"{alert.risk_level.upper()} RISK").classes("risk-level")
                    ui.label(f"{alert.risk_score:.1f}").classes("risk-score")
                    ui.label(alert.physical_impact).classes("guide-copy")
                    ui.linear_progress(value=alert.risk_score / 100).props(
                        "color=negative track-color=blue-grey-10 size=6px"
                    ).classes("w-full")
                with ui.column().classes("panel gap-0"):
                    ui.label("Recommended sequence").classes("section-title")
                    for number, action in enumerate(alert.recommended_actions, start=1):
                        with ui.element("div").classes("action-row"):
                            ui.label(f"{number:02d}").classes("action-number")
                            ui.label(action).classes("action-copy")
                ui.label(alert.safety_note).classes("safety-note")
            else:
                with ui.column().classes("finding"):
                    ui.label("No response required").classes("finding-title")
                    ui.label("Continue normal monitoring.").classes("finding-copy")

        with ui.column().classes("section gap-6").props("id=glossary"):
            _section_heading(
                "06 / QUICK REFERENCE",
                "Terms used on this page",
                "A compact reference for readers without a background in cyber-physical systems.",
            )
            with ui.column().classes("panel gap-0"):
                terms = (
                    (
                        "Digital twin",
                        "An independent model that predicts how the plant should behave.",
                    ),
                    (
                        "Residual",
                        "The difference between an observed value and the twin prediction.",
                    ),
                    ("SOC", "Battery state of charge: the fraction of usable stored energy."),
                    (
                        "Confidence",
                        "How strongly the combined evidence supports an anomaly decision.",
                    ),
                    ("F1 score", "A combined measure of detection precision and recall."),
                )
                for term, definition in terms:
                    with ui.element("div").classes("glossary-row"):
                        ui.label(term).classes("glossary-term")
                        ui.label(definition).classes("glossary-definition")

        ui.label(
            "CPS Sentinel · Deterministic research prototype · No autonomous control actuation"
        ).classes("footer")


def _render_track_unavailable(title: str, state: ExternalTrackState, command: str) -> None:
    with ui.column().classes("w-full gap-0"):
        ui.label("EXTERNAL VALIDATION TRACK").classes("eyebrow")
        ui.label(title).classes("hero-title")
        ui.label(
            "This view activates from generated local results. Raw research datasets remain "
            "outside the web interface and outside version control."
        ).classes("hero-copy")
        with ui.column().classes("section gap-5"), ui.column().classes("empty-state gap-3"):
            ui.label("Validation result not available").classes("finding-title")
            ui.label(state.message).classes("finding-copy")
            ui.label("Run from the project terminal:").classes("metric-label")
            ui.code(command).classes("w-full")


def _render_health_dashboard(state: ExternalTrackState) -> None:
    if not isinstance(state.result, HealthDashboardResult):
        _render_track_unavailable(
            "Battery degradation before failure.",
            state,
            "cps-sentinel health --config config/default.yaml "
            "--input data/raw/nasa/battery-aging-fy08q4 "
            "--output data/processed/nasa-battery-health.csv",
        )
        return
    result = state.result
    latest = result.frame.sort_values("cycle_index").groupby("battery_id").tail(1)
    critical = int((latest["health_status"] == "critical").sum())
    with ui.column().classes("w-full gap-0"):
        ui.label("NASA BATTERY VALIDATION").classes("eyebrow")
        ui.label("Battery degradation before failure.").classes("hero-title")
        ui.label(
            "This track follows measured discharge capacity over repeated cycles, estimates "
            "remaining useful life, and translates degradation into maintenance-oriented alerts."
        ).classes("hero-copy")
        with ui.row().classes("status-line items-center gap-4 w-full"):
            ui.element("span").classes("status-dot").style("background: var(--cyan)")
            ui.label("Real NASA validation loaded").classes("status-text track-ready")

        with ui.element("div").classes("metric-grid"):
            _metric("Batteries", str(result.frame["battery_id"].nunique()), "Independent cells")
            _metric("Discharge cycles", f"{len(result.frame):,}", "Measured capacity tests")
            _metric("Critical latest state", str(critical), "At or below configured SOH limit")
            _metric(
                "RUL error",
                f"{result.evaluation.mae_cycles:.2f} cycles",
                f"{result.evaluation.evaluated_predictions} evaluated forecasts",
            )

        with ui.column().classes("section gap-6").props("id=health-evidence"):
            _section_heading(
                "01 / DEGRADATION EVIDENCE",
                "How quickly is usable capacity disappearing?",
                "Capacity and state of health are physical measurements. The remaining-life line "
                "is a causal projection made using only information available at that cycle.",
            )
            _reading_guide(
                "How to read this report",
                "A downward capacity trend means less stored energy is available. The dotted "
                "observed-RUL line is retrospective evaluation evidence, not an input to forecasts.",
            )
            with ui.element("div").classes("chart-wrap"):
                ui.plotly(build_health_dashboard_figure(result, SETTINGS)).classes("w-full")

        with ui.column().classes("section gap-6").props("id=health-alerts"):
            _section_heading(
                "02 / MAINTENANCE PRIORITIES",
                "Which batteries need attention?",
                "Each row reflects the latest measured cycle and keeps recommendations advisory.",
            )
            for alert in result.alerts:
                with ui.column().classes("panel gap-3"):
                    ui.label(f"{alert.battery_id} / {alert.health_status.upper()}").classes(
                        "risk-level"
                    )
                    ui.label(f"SOH {alert.state_of_health:.1%}").classes("finding-title")
                    ui.label(alert.physical_impact).classes("guide-copy")
                    ui.label(alert.recommended_actions[0]).classes("action-copy")
            ui.label(result.alerts[0].safety_note).classes("safety-note")

        ui.label("CPS Sentinel · NASA health validation · Prognostics are advisory").classes(
            "footer"
        )


def _render_swat_dashboard(state: ExternalTrackState) -> None:
    if not isinstance(state.result, SwatDashboardResult):
        _render_track_unavailable(
            "Industrial attacks in real process data.",
            state,
            "cps-sentinel swat --config config/default.yaml "
            "--normal data/raw/itrust/<normal-file> "
            "--attack data/raw/itrust/<attack-file> "
            "--output data/processed/swat-security.csv",
        )
        return
    result = state.result
    evaluation = result.evaluation
    with ui.column().classes("w-full gap-0"):
        ui.label("ITRUST SWAT VALIDATION").classes("eyebrow")
        ui.label("Industrial attacks in real process data.").classes("hero-title")
        ui.label(
            "This track learns normal relationships among water-treatment sensors and actuators, "
            "then evaluates persistent deviations against labels withheld during detection."
        ).classes("hero-copy")
        with ui.row().classes("status-line items-center gap-4 w-full"):
            ui.element("span").classes("status-dot").style("background: var(--cyan)")
            ui.label("Authorized SWaT validation loaded").classes("status-text track-ready")

        with ui.element("div").classes("metric-grid"):
            _metric("Historian rows", f"{evaluation.rows:,}", "Labeled attack run")
            _metric("Point F1", f"{evaluation.f1:.3f}", "Precision and recall balance")
            _metric("Event recall", f"{evaluation.event_recall:.1%}", "Attack intervals detected")
            _metric(
                "False-positive rate",
                f"{evaluation.false_positive_rate:.2%}",
                "Normal rows flagged",
            )

        with ui.column().classes("section gap-6").props("id=swat-evidence"):
            _section_heading(
                "01 / INDUSTRIAL EVIDENCE",
                "When did process behavior become abnormal?",
                "The score combines multivariate novelty and explicit process deviation, then "
                "requires persistence before creating an event.",
            )
            _reading_guide(
                "Labels are evaluation only",
                "The red attack trace is displayed after scoring. It never participates in model "
                "training, clean-data calibration, or anomaly decisions.",
            )
            with ui.element("div").classes("chart-wrap"):
                ui.plotly(build_swat_dashboard_figure(result)).classes("w-full")

        with ui.column().classes("section gap-6").props("id=swat-events"):
            _section_heading(
                "02 / EVENT REVIEW",
                "Which process tags carried the evidence?",
                "Events rank the tags with the largest standardized deviations for investigation.",
            )
            for event in result.events[:12]:
                with ui.column().classes("panel gap-3"):
                    ui.label(event.event_id).classes("metric-label")
                    ui.label(", ".join(event.top_affected_tags) or "No leading tag").classes(
                        "finding-title"
                    )
                    ui.label(event.physical_context).classes("guide-copy")
                    ui.label(
                        "Overlaps a labeled attack"
                        if event.overlaps_labeled_attack
                        else "No label overlap"
                    ).classes("action-copy")

        ui.label(
            "CPS Sentinel · iTrust SWaT validation · Raw historian data is never exposed"
        ).classes("footer")


def build_page() -> None:
    """Build one client-private dashboard page."""
    state: dict[str, Any] = {
        "mode": "nanogrid",
        "result": run_dashboard_scenario(str(CONFIG_PATH), str(CATALOG[DEFAULT_SCENARIO])),
    }
    health_state = load_health_dashboard_result(HEALTH_RESULT_PATH)
    swat_state = load_swat_dashboard_result(SWAT_RESULT_PATH, SETTINGS)

    def change_mode(mode: str) -> None:
        state["mode"] = mode
        content.refresh()

    async def change_scenario(event: events.ValueChangeEventArguments) -> None:
        path = CATALOG[str(event.value)]
        ui.notify("Running scenario analysis", type="ongoing", timeout=1200)
        state["result"] = await run.io_bound(run_dashboard_scenario, str(CONFIG_PATH), str(path))
        content.refresh()

    drawer = ui.left_drawer().props("width=280 breakpoint=1050 show-if-above bordered")
    with drawer, ui.column().classes("w-full px-4 pt-5 gap-0"):
        with ui.row().classes("items-center gap-3 px-2"):
            ui.html('<div class="brand-mark">CS</div>')
            with ui.column().classes("gap-0"):
                ui.label("CPS Sentinel").classes("brand-name")
                ui.label("System monitor").classes("brand-sub")
        ui.label("Navigate").classes("nav-label")
        for label, mode, marker in (
            ("Nanogrid monitor", "nanogrid", "mode-nanogrid"),
            ("Battery health", "health", "mode-health"),
            ("SWaT security", "swat", "mode-swat"),
        ):
            ui.button(label, on_click=lambda selected=mode: change_mode(selected)).props(
                "flat no-caps align=left"
            ).classes("mode-button").mark(marker)
        ui.label("Nanogrid sections").classes("nav-label")
        for label, target in (
            ("Incident overview", "overview"),
            ("Sensor evidence", "sensor"),
            ("Physical consequence", "impact"),
            ("Detection logic", "detection"),
            ("Operator response", "response"),
            ("Quick reference", "glossary"),
        ):
            ui.button(label, on_click=lambda section=target: _jump_to(section)).props(
                "flat no-caps align=left"
            ).classes("nav-button")
        ui.label("Scenario").classes("nav-label")
        ui.select(
            options=list(CATALOG),
            value=DEFAULT_SCENARIO,
            on_change=change_scenario,
        ).props("outlined dense options-dense").classes("scenario-select w-full px-2").mark(
            "scenario-select"
        )
        with ui.column().classes("mt-7 px-3 gap-2"):
            ui.label("Analysis pipeline").classes("metric-label")
            ui.label("Simulation → Twin → Detection → Risk").classes("guide-copy")
            ui.label("Labels are used only for evaluation.").classes("guide-copy")

    with ui.header().classes("h-16 items-center px-4"):
        ui.button(icon="menu", on_click=drawer.toggle).props(
            "flat round aria-label=Open_navigation"
        ).classes("mobile-menu").mark("mobile-menu")
        ui.label("CPS SENTINEL / UNIFIED OPERATIONS").classes("status-text")
        ui.space()
        ui.label("PHASE 9").classes("status-text")

    with ui.column().classes("page-shell gap-0"):

        @ui.refreshable
        def content() -> None:
            if state["mode"] == "health":
                _render_health_dashboard(health_state)
            elif state["mode"] == "swat":
                _render_swat_dashboard(swat_state)
            else:
                _render_dashboard(state["result"])

        content()


ui.add_css(CSS)
ui.colors(primary="#42c6d7", secondary="#e5a93d", negative="#e66565")
IS_PYTEST = "PYTEST_CURRENT_TEST" in os.environ
if not IS_PYTEST:
    build_page()

if __name__ in {"__main__", "__mp_main__"} and not IS_PYTEST:
    ui.run(
        title="CPS Sentinel | System Monitor",
        favicon=FAVICON,
        host="127.0.0.1",
        port=int(os.environ.get("CPS_SENTINEL_PORT", "8080")),
        dark=True,
        reload=False,
        show=True,
        show_welcome_message=True,
    )
