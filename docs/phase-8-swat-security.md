# Phase 8: iTrust SWaT security validation

## Goal

Phase 8 validates CPS Sentinel on historian data from the Secure Water Treatment (SWaT)
industrial testbed. This is an external security track: it does not pretend that water-treatment
tags belong to the nanogrid digital twin.

The canonical SWaT.A1 December 2015 dataset contains seven days of normal operation followed by
four days containing 41 labeled attacks across 51 sensors and actuators. The raw files remain local
under the iTrust terms and are never committed, uploaded, or redistributed.

## Data contract

The loader accepts authorized normal and labeled attack historian files in CSV or XLSX format. It:

- normalizes timestamp and label-column variants;
- converts common actuator states such as `Active` and `Inactive` to numeric values;
- retains numeric sensor and actuator tags;
- emits `timestamp`, `is_attack`, and normalized tag columns;
- supports deterministic row-stride sampling for constrained machines.

## Time-safe detection

The first configured fraction of the normal run fits the imputer, scaler, and Isolation Forest.
The remaining normal tail calibrates an anomaly-score threshold. Level and first-difference
features capture both abnormal process states and abnormal transitions. Training can be capped by
deterministic subsampling, while scoring still covers every loaded attack row.

Attack labels are withheld from preprocessing, feature fitting, threshold calibration, and model
scoring. They are used only after detection to calculate precision, recall, F1, false-positive
rate, event recall, and detection delay.

## Explainable outputs

Persistent row flags are aggregated into events. Each event records:

- its start, end, duration, and peak anomaly score;
- whether it overlaps a labeled attack;
- the process tags with the largest standardized deviations;
- bounded investigation and evidence-preservation actions;
- an explicit operator-confirmation safety boundary.

The interactive report aligns anomaly score, clean-data threshold, labeled attacks, persistent
detections, and frequently implicated tags on one timeline.

## Run locally

```bash
cps-sentinel swat \
  --config config/default.yaml \
  --normal data/raw/itrust/SWaT_Dataset_Normal_v1.csv \
  --attack data/raw/itrust/SWaT_Dataset_Attack_v0.csv \
  --output data/processed/swat-security.csv \
  --events data/processed/swat-security-events.json \
  --plot reports/figures/swat-security.html
```

Use `--sample-stride 5` for an initial lower-memory smoke run, then use the default stride of one
for the final benchmark.

## Acceptance criteria

- Raw SWaT files and generated outputs remain excluded from Git.
- Normal and attack schema variants are normalized without silently retaining the label as a tag.
- No attack row or attack label participates in training or threshold calibration.
- Point-level and event-level metrics are reported separately.
- Events identify leading affected tags and provide bounded operator guidance.
- Synthetic contract tests and the complete project quality suite pass before real-data execution.
