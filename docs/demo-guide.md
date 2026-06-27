# Demo guide

This guide packages CPS Sentinel into a repeatable portfolio demonstration. Use it for a GitHub
walkthrough, CV interview, or live demo.

## Thirty-second pitch

CPS Sentinel is a digital-twin cyber-physical systems monitoring prototype. It simulates a smart
nanogrid, injects cyberattacks and faults, compares sensor evidence against an independent digital
twin, detects persistent anomalies, ranks physical risk, and explains bounded operator responses.
It also validates the same monitoring language on NASA battery aging data and iTrust SWaT
industrial process data.

## Five-minute demo flow

1. **Start with the architecture**
   - Open [architecture.md](architecture.md).
   - Explain that the nanogrid is the main CPS product and NASA/SWaT are external validation
     tracks.
   - Emphasize that the digital twin remains independent from compromised sensor measurements.

2. **Run the dashboard**

   ```bash
   python app/nicegui_app.py
   ```

   If port 8080 is busy:

   ```bash
   CPS_SENTINEL_PORT=8081 python app/nicegui_app.py
   ```

   Show the nanogrid monitor first, then quickly switch to Battery health and SWaT security.

3. **Show the benchmark matrix**

   ```bash
   cps-sentinel benchmark \
     --config config/default.yaml \
     --scenario-dir config/scenarios \
     --output reports/benchmarks/scenario-benchmark.csv \
     --report reports/benchmarks/scenario-benchmark.md
   ```

   Point out that one clean baseline detector is reused across all scenario YAMLs. Current local
   result: 8/8 events detected with average F1 0.886.

4. **Show the operator incident report**

   ```bash
   cps-sentinel report \
     --config config/default.yaml \
     --scenario config/scenarios/pv-false-data-injection.yaml \
     --output reports/incidents/nanogrid-incident-report.md
   ```

   This demonstrates how the project turns model output into an operator-readable incident
   artifact with evidence, risk factors, recommended actions, and a safety boundary.

5. **Show reproducibility**

   ```bash
   cps-sentinel demo \
     --config config/default.yaml \
     --output-dir reports/demo
   ```

   This regenerates local evidence artifacts without committing generated data or restricted raw
   datasets.

## Commands worth memorizing

```bash
pytest --cov --cov-report=term-missing
ruff check .
mypy src
cps-sentinel benchmark --config config/default.yaml
cps-sentinel report --config config/default.yaml
```

## Artifacts to show

| Artifact | Why it matters |
| --- | --- |
| `README.md` | Shows the complete public-facing project overview and Mermaid architecture. |
| `app/nicegui_app.py` | Shows the unified NiceGUI operations dashboard. |
| `docs/architecture.md` | Shows the system boundary and validation tracks. |
| `docs/project-brief.md` | Gives a one-page explanation for recruiters and reviewers. |
| `docs/cv-project-summary.md` | Contains CV-ready bullets and interview talking points. |
| `reports/benchmarks/scenario-benchmark.md` | Local generated evidence that all scenarios were benchmarked. |
| `reports/incidents/nanogrid-incident-report.md` | Local generated operator-facing incident report. |

## Strong CV bullet

Built CPS Sentinel, a Python/NiceGUI digital-twin CPS monitoring prototype that simulates
nanogrid attacks/faults, calibrates detectors only on clean data, detects events across 8/8
committed scenarios with average F1 0.886, ranks physical risk, exports operator incident reports,
and validates health/security tracks on NASA battery and iTrust SWaT data.

## Interview talking points

- **No label leakage:** scenario labels are withheld during detection and used only afterward for
  evaluation.
- **Digital twin boundary:** expected behavior is produced independently from attacked sensor
  readings.
- **Safety boundary:** recommendations are decision support only, never autonomous actuation.
- **External validation:** NASA and SWaT tracks validate methods on real datasets while keeping raw
  restricted data out of Git.
- **Honest limitations:** SWaT is useful at event level, while point-level recall remains an
  improvement area.
