# CPS Sentinel

**Digital Twin-Based Security and Health Monitoring for Cyber-Physical Systems**

CPS Sentinel is a portfolio-grade research prototype for detecting, explaining, and
responding to faults and cyberattacks in cyber-physical systems. Its central system is a
simulated smart nanogrid paired with a physics-aware digital twin.

NASA battery data will provide an external health-prognostics validation track. The iTrust
SWaT dataset will provide a separate industrial attack-detection validation track. These
tracks share evaluation and alert interfaces; they are not treated as one physical system.

[View the overall architecture as a PDF](output/pdf/cps-sentinel-overall-architecture.pdf).

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
terminal. It provides selectable attack and fault scenarios, plain-language incident explanations,
physical-system versus digital-twin evidence, evaluation metrics, risk-ranked alerts, and
operator-confirmed response recommendations.

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
