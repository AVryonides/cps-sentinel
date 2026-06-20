# Phase 5: Risk assessment and bounded response guidance

## Purpose

Phase 5 converts Phase 4 event detections into prioritized operator decisions. It answers four
questions for every event: how credible is it, what physical consequence is visible, how long has
it persisted, and how close is the battery to its configured SOC limits?

## Explainable risk score

Each factor is normalized to the interval `[0, 1]`, then combined into a score from 0 to 100:

```text
risk = 100 * (0.30 confidence + 0.40 impact + 0.15 duration + 0.15 safety proximity)
```

Impact is the largest normalized consequence among grid-power divergence, sensor-balance error,
SOC divergence, and battery-command deviation. Duration reaches its configured maximum after 36
steps (three hours at the default five-minute timestep). Safety proximity increases as observed
SOC approaches either configured battery limit. Weights, reference values, and Low/Medium/High/
Critical thresholds are all defined in `config/default.yaml`.

## Alert contract

Every alert contains event identity and timing, diagnosis and affected component, detector
confidence, total risk and factor breakdown, peak physical-impact measurements, evidence,
recommended actions, and an explicit safety note. Alerts are sorted highest-risk first and written
as portable JSON.

## Response policy

Recommendations depend on the diagnosed component. Sensor-integrity events call for distrusting
the affected telemetry, substituting only bounded twin estimates, and cross-checking independent
measurements. Command-path events call for blocking the suspect path and holding a bounded,
last-verified setpoint. Battery and power-flow anomalies call for reduced limits and conservative
grid-supported operation.

This phase does **not** actuate the nanogrid. Guidance is advisory, reversible, and requires a
qualified operator to approve control actions and restoration. It is a research prototype, not a
certified safety controller.

## Reproduction

```bash
cps-sentinel assess \
  --config config/default.yaml \
  --scenario config/scenarios/pv-false-data-injection.yaml \
  --output data/simulated/pv-fdi-assessment.csv \
  --alerts data/simulated/pv-fdi-alerts.json \
  --plot reports/figures/pv-fdi-risk.html
```

Acceptance requires a detected catalog scenario to produce a bounded 0-100 risk score, a ranked
JSON alert, a diagnosis-specific reversible response, a physical-impact narrative, and an
interactive report without consulting ground-truth labels during scoring.
