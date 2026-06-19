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
6. Demonstrate the scenario in Streamlit.

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

Run the dashboard:

```bash
streamlit run app/streamlit_app.py
```

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
