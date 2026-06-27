# Phase 14: scenario benchmark matrix

Phase 14 adds a committed-code benchmark command for the nanogrid scenario catalog. Instead of
showing only the flagship PV false-data injection case, CPS Sentinel can now evaluate every
scenario YAML with one detector calibrated on clean baseline behavior.

## Command

```bash
cps-sentinel benchmark \
  --config config/default.yaml \
  --scenario-dir config/scenarios \
  --output reports/benchmarks/scenario-benchmark.csv \
  --report reports/benchmarks/scenario-benchmark.md
```

Generated benchmark files under `reports/benchmarks/` are ignored by Git because they are local
artifacts.

## What the benchmark contains

- scenario name and source YAML path;
- scenario kind, target, and attack/fault label;
- active event duration;
- precision, recall, F1, false-positive rate, and detection delay;
- whether an event was detected;
- alert count, top risk score, risk level, likely event, and affected component;
- Markdown summary table for portfolio/interview review.

## Evaluation boundary

The detector is fitted once on clean baseline nanogrid behavior. Scenario labels are used only
after detection to calculate evaluation metrics. This keeps the benchmark aligned with the
project's clean-calibration and no-label-leakage principle.

## Acceptance criteria

- One command evaluates every committed scenario YAML.
- The benchmark writes both CSV and Markdown artifacts.
- Generated benchmark artifacts are ignored by Git.
- Tests assert that the command evaluates the full scenario catalog and writes the report.
