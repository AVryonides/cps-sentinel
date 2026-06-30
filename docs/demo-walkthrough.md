# Demo walkthrough

This walkthrough presents CPS Sentinel as a repeatable technical demonstration. It is intended for
reviewers who want to understand the system boundary, reproduce the main evidence flow, and inspect
the generated artifacts without relying on restricted raw datasets.

## Short project summary

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

## Core commands

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
| `docs/technical-overview.md` | Summarizes implementation, results, and data boundaries. |
| `reports/benchmarks/scenario-benchmark.md` | Local generated evidence that all scenarios were benchmarked. |
| `reports/incidents/nanogrid-incident-report.md` | Local generated operator-facing incident report. |
