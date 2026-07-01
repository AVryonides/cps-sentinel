# CPS Sentinel showcase guide

This guide is a concise path for reviewing CPS Sentinel as a completed cyber-physical systems
research prototype. It focuses on what the project demonstrates, how to reproduce the main
evidence, and where to inspect the implementation.

## Review path

1. Start with the [README](README.md) for the architecture diagram, dashboard screenshots, current
   validation results, setup instructions, and core workflows.
2. Open [docs/architecture.md](docs/architecture.md) to understand the product boundary:
   the smart nanogrid is the main CPS system, while NASA battery and iTrust SWaT datasets are
   external validation tracks.
3. Run the dashboard:

   ```bash
   python app/nicegui_app.py
   ```

4. Generate the reproducible local evidence bundle:

   ```bash
   cps-sentinel demo \
     --config config/default.yaml \
     --output-dir reports/demo
   ```

5. Inspect the benchmark and incident-report workflows:

   ```bash
   cps-sentinel benchmark \
     --config config/default.yaml \
     --scenario-dir config/scenarios \
     --output reports/benchmarks/scenario-benchmark.csv \
     --report reports/benchmarks/scenario-benchmark.md

   cps-sentinel report \
     --config config/default.yaml \
     --scenario config/scenarios/pv-false-data-injection.yaml \
     --output reports/incidents/nanogrid-incident-report.md
   ```

## Evidence map

| Evidence | Where to inspect it | What it demonstrates |
| --- | --- | --- |
| Digital-twin residuals | `src/cps_sentinel/twin/`, `src/cps_sentinel/detection/` | Expected behavior is produced independently from attacked measurements. |
| Attack and fault scenarios | `config/scenarios/` | Reproducible disturbance definitions with labels withheld from detection. |
| Risk scoring | `src/cps_sentinel/risk/` | Alerts are ranked by confidence, physical impact, duration, and safety proximity. |
| Operator report | `src/cps_sentinel/incident_report.py` | Model output is translated into a bounded, readable incident artifact. |
| Dashboard | `app/nicegui_app.py` | The system presents evidence, assumptions, limits, and response guidance interactively. |
| External validation | `src/cps_sentinel/health/`, `src/cps_sentinel/swat/` | The monitoring approach is evaluated on NASA battery and iTrust SWaT tracks. |

## Current validation snapshot

| Track | Result |
| --- | --- |
| Nanogrid flagship scenario | F1 0.972, risk score 95.2/100, one persistent incident |
| Nanogrid scenario benchmark | 8/8 committed scenarios detected, average F1 0.886 |
| NASA battery health | 4 batteries, 636 discharge cycles, RUL MAE 8.99 cycles |
| iTrust SWaT security | 5/6 scheduled attacks detected, point F1 0.446, false-positive rate 11.93% |

The SWaT result is intentionally reported with its limitation: the current detector is stronger at
event-level detection than point-level classification.

## Quality checks

The project is validated with:

```bash
pytest --cov --cov-report=term-missing
ruff check .
mypy src
```

The GitHub CI workflow runs the same quality gate on Python 3.11, 3.12, and 3.13.

## Data boundary

Raw and processed datasets are excluded from Git. Restricted iTrust SWaT data must be requested
directly from iTrust and kept local. The repository contains source code, configuration,
documentation, screenshots, and public derived metrics only.

## Safety boundary

CPS Sentinel provides decision support. It does not send control commands, perform autonomous
actuation, or claim production readiness. Recommended actions are advisory, bounded, and intended
for review by a qualified operator.
