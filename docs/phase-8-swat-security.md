# Phase 8: iTrust SWaT security validation

## Goal

Phase 8 validates CPS Sentinel on historian data from the Secure Water Treatment (SWaT)
industrial testbed. This is an external security track: it does not pretend that water-treatment
tags belong to the nanogrid digital twin.

The completed local validation uses the official SWaT.A4/A5 July 2019 release because it is
compact enough to handle locally and includes a companion collection note with the attack
schedule. The raw files remain local under the iTrust terms and are never committed, uploaded, or
redistributed.

## Data contract

The loader accepts authorized normal and labeled attack historian files in CSV or XLSX format. It
also supports a single scheduled run, where labels are derived from official attack windows. It:

- normalizes timestamp and label-column variants;
- converts common actuator states such as `Active` and `Inactive` to numeric values;
- handles SWaT.A4/A5 two-row historian headers;
- retains numeric sensor and actuator tags;
- emits `timestamp`, `is_attack`, and normalized tag columns;
- supports deterministic row-stride sampling for constrained machines.

## Time-safe detection

The first configured fraction of the normal run fits the imputer, scaler, and Isolation Forest.
The remaining normal tail calibrates an anomaly-score threshold. Level and first-difference
features capture both abnormal process states and abnormal transitions. Training can be capped by
deterministic subsampling, while scoring still covers every loaded attack row.

For SWaT.A4/A5, clean data up to one second before the first documented attack is used for
training and threshold calibration. Attack-window labels are withheld from preprocessing, feature
fitting, threshold calibration, and model scoring. They are used only after detection to calculate
precision, recall, F1, false-positive rate, event recall, and detection delay.

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
  --scheduled-run "data/raw/itrust/SWaT.A4 & A5_Jul 2019/SWaT_dataset_Jul 19 v2.xlsx" \
  --schedule swat-a4-a5-jul-2019 \
  --output data/processed/swat-security.csv \
  --events data/processed/swat-security-events.json \
  --plot reports/figures/swat-security.html
```

Use `--sample-stride 5` for an initial lower-memory smoke run, then use the default stride of one
for the final benchmark. If the larger SWaT.A1/A2 historian-only files become available, the
original two-file mode remains supported through `--normal` and `--attack`.

## Current local result

Official SWaT.A4/A5 July 2019 run:

- clean training/calibration rows: 9,221;
- evaluated rows: 4,052;
- labeled attack rows: 1,981;
- point precision: 0.722;
- point recall: 0.323;
- point F1: 0.446;
- false-positive rate: 0.119;
- scheduled attack events detected: 5 of 6;
- aggregated operator-facing detection events: 7.

This is intentionally reported as a transparent baseline rather than an over-claimed result: the
detector is useful at the event level, while point-level recall remains a future improvement area.

## Acceptance criteria

- Raw SWaT files and generated outputs remain excluded from Git.
- Normal and attack schema variants are normalized without silently retaining the label as a tag.
- No attack row or attack label participates in training or threshold calibration.
- Point-level and event-level metrics are reported separately.
- Events identify leading affected tags and provide bounded operator guidance.
- Synthetic contract tests and the complete project quality suite pass before real-data execution.
