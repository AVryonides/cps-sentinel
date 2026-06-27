# CPS Sentinel

**Digital Twin-Based Security and Health Monitoring for Cyber-Physical Systems**

[![CI](https://github.com/AVryonides/cps-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/AVryonides/cps-sentinel/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11--3.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

CPS Sentinel is a portfolio-grade research prototype for detecting, explaining, and
responding to faults and cyberattacks in cyber-physical systems. Its central system is a
simulated smart nanogrid paired with a physics-aware digital twin.

NASA battery data provides an external health-prognostics validation track. The iTrust
SWaT dataset provides a separate industrial attack-detection validation track. These
tracks share evaluation and alert interfaces; they are not treated as one physical system.

The project is built to demonstrate an end-to-end CPS engineering workflow: simulation,
digital-twin prediction, attack/fault injection, hybrid anomaly detection, risk scoring,
operator guidance, dashboard explainability, and reproducible demo packaging.

- [One-page project brief](docs/project-brief.md)
- [CV-ready project summary](docs/cv-project-summary.md)
- [Overall architecture PDF](output/pdf/cps-sentinel-overall-architecture.pdf)

## What this project demonstrates

- A physics-aware nanogrid simulator with PV generation, load, battery state of charge, and
  grid exchange.
- An independent digital twin that produces expected behavior and residual evidence.
- Scenario-driven cyberattack/fault injection with ground-truth labels kept separate from
  detection.
- Hybrid detection using robust physical thresholds, statistical novelty, and temporal
  persistence.
- Risk-ranked, bounded response recommendations for human operators.
- External validation tracks for NASA battery prognostics and iTrust SWaT industrial
  attack detection.
- A NiceGUI operations dashboard designed for explainability, not just charts.
- A reproducible `cps-sentinel demo` workflow that regenerates local evidence artifacts.

## Current validation snapshot

| Track | Dataset / source | Current result |
| --- | --- | --- |
| Nanogrid attack demo | Deterministic smart-nanogrid scenario | F1 0.972, risk score 95.2/100, one persistent incident |
| Battery health | NASA battery aging data | 4 batteries, 636 discharge cycles, RUL MAE 8.99 cycles |
| Industrial security | iTrust SWaT.A4/A5 July 2019 | 5/6 scheduled attacks detected, point F1 0.446, FPR 11.93% |

The SWaT point-level score is intentionally reported honestly: current performance is useful at
incident/event level, while point recall remains a future-improvement target.

## Planned vertical slice

1. Simulate PV generation, load, battery state of charge, and grid exchange.
2. Predict expected behavior with a physics-aware digital twin.
3. Inject a PV-sensor false-data attack.
4. Detect the resulting residual and physical inconsistency.
5. Produce an explainable, risk-ranked response recommendation.
6. Demonstrate the complete reasoning chain in a NiceGUI web application.

## Development setup

The project supports Python 3.11–3.13. Python 3.11 is used for local development.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest --cov
ruff check .
mypy src
```

Run the configuration smoke check:

```bash
cps-sentinel validate --config config/default.yaml
```

Run the Phase 1 nanogrid simulator:

```bash
cps-sentinel simulate \
  --config config/default.yaml \
  --output data/simulated/baseline.csv \
  --plot reports/figures/baseline.html
```

Run the Phase 2 independent digital twin:

```bash
cps-sentinel twin \
  --config config/default.yaml \
  --output data/simulated/twin-baseline.csv \
  --plot reports/figures/twin-baseline.html
```

Run a Phase 3 closed-loop attack scenario:

```bash
cps-sentinel scenario \
  --config config/default.yaml \
  --scenario config/scenarios/pv-false-data-injection.yaml \
  --output data/simulated/pv-fdi.csv \
  --plot reports/figures/pv-fdi.html
```

Run Phase 4 hybrid detection and diagnosis:

```bash
cps-sentinel detect \
  --config config/default.yaml \
  --scenario config/scenarios/pv-false-data-injection.yaml \
  --output data/simulated/pv-fdi-detection.csv \
  --events data/simulated/pv-fdi-events.json \
  --plot reports/figures/pv-fdi-detection.html
```

Run Phase 5 risk assessment and bounded response guidance:

```bash
cps-sentinel assess \
  --config config/default.yaml \
  --scenario config/scenarios/pv-false-data-injection.yaml \
  --output data/simulated/pv-fdi-assessment.csv \
  --alerts data/simulated/pv-fdi-alerts.json \
  --plot reports/figures/pv-fdi-risk.html
```

Run the dashboard:

```bash
python app/nicegui_app.py
```

The dashboard opens automatically at `http://localhost:8080` and also prints the address in the
terminal. Its unified navigation includes the nanogrid attack/fault demonstrator, NASA battery
health validation, and iTrust SWaT security validation. External views read generated processed
results only; restricted raw datasets are never exposed by the web layer. The interface uses
explanation cards, metric interpretation, operational summaries, and stronger data-boundary
messaging so the dashboard reads as a demo-ready incident story rather than a collection of plots.

See [the Phase 10 dashboard polish note](docs/phase-10-dashboard-polish.md) for the explainability
and data-boundary design choices.

Generate a reproducible local demo bundle:

```bash
cps-sentinel demo \
  --config config/default.yaml \
  --output-dir reports/demo
```

This writes a local summary report, manifest, nanogrid CSV/JSON outputs, and interactive HTML
reports under `reports/demo/`. If NASA or SWaT processed outputs already exist locally, they are
summarized too; otherwise the report records the exact commands needed to generate them. See
[the Phase 11 reproducible demo note](docs/phase-11-reproducible-demo.md) for details.

Generate an operator-facing incident report:

```bash
cps-sentinel report \
  --config config/default.yaml \
  --scenario config/scenarios/pv-false-data-injection.yaml \
  --output reports/incidents/nanogrid-incident-report.md
```

This writes a local Markdown report with an executive summary, detection metrics, primary alert,
evidence, risk-factor breakdown, recommended operator sequence, and safety boundary. See
[the Phase 13 incident-report note](docs/phase-13-incident-report.md) for details.

Generate a scenario benchmark matrix:

```bash
cps-sentinel benchmark \
  --config config/default.yaml \
  --scenario-dir config/scenarios \
  --output reports/benchmarks/scenario-benchmark.csv \
  --report reports/benchmarks/scenario-benchmark.md
```

This evaluates every committed nanogrid scenario YAML with one clean baseline detector
calibration and writes CSV/Markdown benchmark artifacts. See
[the Phase 14 benchmark note](docs/phase-14-scenario-benchmark.md) for details.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/cps_sentinel/` | Simulation, twin, detection, risk, health, SWaT, and demo workflow code |
| `app/nicegui_app.py` | Unified NiceGUI operations dashboard |
| `config/default.yaml` | Main model, detector, risk, and health configuration |
| `config/scenarios/` | Reproducible attack/fault scenario definitions |
| `docs/` | Phase notes, architecture notes, project brief, and CV summary |
| `reports/demo/` | Local generated demo artifacts; ignored by Git |
| `reports/incidents/` | Local generated incident reports; ignored by Git |
| `reports/benchmarks/` | Local generated scenario benchmark artifacts; ignored by Git |
| `data/raw/` | Local-only restricted datasets; ignored by Git |

Run Phase 7 NASA battery health validation after downloading and extracting the official archive:

```bash
cps-sentinel health \
  --config config/default.yaml \
  --input data/raw/nasa/battery-aging-fy08q4 \
  --output data/processed/nasa-battery-health.csv \
  --alerts data/processed/nasa-health-alerts.json \
  --plot reports/figures/nasa-battery-health.html
```

The health track extracts discharge capacity, calculates state of health, performs causal
remaining-useful-life projection, evaluates predictions against observed end of life, and emits
maintenance-oriented health alerts.

Run Phase 8 iTrust SWaT security validation with the authorized SWaT.A4/A5 July 2019
historian workbook and companion attack schedule:

```bash
cps-sentinel swat \
  --config config/default.yaml \
  --scheduled-run "data/raw/itrust/SWaT.A4 & A5_Jul 2019/SWaT_dataset_Jul 19 v2.xlsx" \
  --schedule swat-a4-a5-jul-2019 \
  --output data/processed/swat-security.csv \
  --events data/processed/swat-security-events.json \
  --plot reports/figures/swat-security.html
```

This external security track learns multivariate process behavior only from clean SWaT data,
detects persistent deviations in the later labeled run, evaluates point and event performance,
and identifies the process tags contributing most strongly to each event.

Current local validation on the official A4/A5 release detects 5 of 6 scheduled attack events
with point precision 0.722, point recall 0.323, F1 0.446, and false-positive rate 0.119.

## Data policy

Raw and processed datasets are excluded from Git. In particular, iTrust datasets must not
be redistributed. See the README files under `data/raw/` for provenance and handling rules.

## Simulator conventions

- Battery power is positive for discharge and negative for charge.
- Grid power is positive for import and negative for export.
- `battery_soc` is the end-of-timestep state of charge.
- Each row satisfies `PV + battery + grid - load = 0`, up to floating-point tolerance.

See [the Phase 1 simulator specification](docs/phase-1-simulator.md) for the physical model,
controller behavior, outputs, and acceptance criteria.

## Digital twin conventions

- Expected values come from time-based reference profiles and independent twin state.
- Observed sensor values are used only to calculate residuals after prediction.
- Every residual uses `observed - expected`.
- The twin makes no attack decision in Phase 2; it exposes evidence for later detection.

See [the Phase 2 digital-twin specification](docs/phase-2-digital-twin.md) for the model
boundary, output schema, residual definitions, and acceptance criteria.

## Scenario conventions

- Scenarios are injected inside the closed control loop, before physical behavior is solved.
- Sensor attacks alter controller inputs; command attacks alter the battery command path.
- Physical faults alter effective battery parameters only during the labeled window.
- Scenario CSVs contain true values, reported values, commands, physical outputs, twin
  expectations, residuals, and exact ground-truth labels.

See [the Phase 3 scenario specification](docs/phase-3-scenarios.md) and the reproducible YAML
examples under [`config/scenarios`](config/scenarios).

## Detection conventions

- Robust physics thresholds and Isolation Forest are fitted only on clean baseline data.
- Scenario labels are withheld from detection and used only afterward for evaluation.
- Temporal persistence suppresses isolated flags before diagnosis and event aggregation.
- Diagnoses are coarse, evidence-backed component hypotheses rather than ground-truth copies.

See [the Phase 4 detection specification](docs/phase-4-detection.md) for feature calibration,
hybrid scoring, diagnosis rules, evaluation metrics, and current limitations.

## Risk and response conventions

- Event risk combines confidence, measured physical impact, duration, and proximity to SOC limits.
- Alerts are ranked from highest to lowest risk and retain the evidence behind their diagnosis.
- Recommended actions are bounded, reversible decision support—not autonomous actuation.
- A qualified operator must confirm control changes and restoration of automatic operation.
