# Phase 13: operator incident report export

Phase 13 adds a written incident-report artifact for the nanogrid scenario pipeline. The
dashboard is useful for live explanation; the report is useful for evidence sharing, interviews,
portfolio review, and operator handoff.

## Command

```bash
cps-sentinel report \
  --config config/default.yaml \
  --scenario config/scenarios/pv-false-data-injection.yaml \
  --output reports/incidents/nanogrid-incident-report.md
```

Generated reports under `reports/incidents/` are ignored by Git because they are local artifacts.

## What the report contains

- plain-language executive summary;
- scenario and reproducibility metadata;
- precision, recall, F1, false-positive rate, and detection delay;
- primary alert time window, risk level, score, confidence, and physical impact;
- evidence bullets from the diagnosis layer;
- risk-factor breakdown;
- recommended operator sequence;
- explicit safety boundary.

## Safety and data boundary

The report is advisory decision support only. It does not send commands to the simulated plant,
does not bypass an operator, and does not read or redistribute restricted NASA or iTrust/SWaT raw
datasets.

## Acceptance criteria

- `cps-sentinel report` writes a Markdown report from committed code and a scenario YAML.
- The report uses the same clean-data calibration and risk-assessment pipeline as the CLI and
  dashboard.
- The report includes rounded operator-readable metrics, not raw internal floating-point values.
- The generated report directory remains ignored by Git.
