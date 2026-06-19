# Phase 4 - Hybrid detection and diagnosis

## High-level purpose

Phase 4 converts digital-twin residuals into persistent detections and explainable events.
It combines interpretable physical evidence with a multivariate statistical model so neither
layer has to solve the entire problem alone.

## No-leakage boundary

The detector is fitted exclusively on a clean Phase 2 baseline. It never receives
`scenario_active`, `ground_truth_label`, scenario kind, target, timing, or intensity as
features. Those columns are used only after detection to measure performance.

This separation is tested and is fundamental to the validity of later experiments.

## Detection features

The feature contract contains:

- PV and load residuals;
- battery-power and grid-power residuals;
- battery-SOC residual;
- reported-measurement power imbalance;
- delivered-minus-requested battery command residual.

## Layer 1 - Physics-aware detection

For each clean-baseline feature, CPS Sentinel calculates:

1. the median center;
2. median absolute deviation (MAD);
3. a robust sigma estimate `1.4826 * MAD`;
4. a high empirical deviation quantile;
5. a small engineering floor in physical units.

The threshold is the maximum of the robust, empirical, and engineering limits. A physics
vote occurs when a feature exceeds its calibrated limit. The breached feature names become
human-readable evidence.

## Layer 2 - Statistical detection

An Isolation Forest is fitted on standardized clean residual features. Scenario rows receive
an anomaly score and an empirical percentile relative to clean training scores.

The model is deterministic for a fixed random seed. It complements physics rules by finding
unusual multivariate combinations, but it does not diagnose an attack type by itself.

## Layer 3 - Temporal correlation and diagnosis

Raw physics/ML flags pass through a configurable rolling persistence vote. Persistent rows
are assigned:

- confidence and severity;
- likely event class;
- affected component;
- evidence and rationale.

The diagnosis rules distinguish coarse hypotheses such as PV-sensor integrity, load-sensor
integrity, battery-command integrity, battery-state divergence, and general power-flow
anomalies. They intentionally avoid claiming an exact attack subtype when evidence cannot
support one.

Contiguous detections are aggregated into event JSON records with start/end timestamps,
duration, maximum confidence, severity, component, diagnosis, and evidence.

## Evaluation

After detection, ground truth is used to calculate:

- point-level precision, recall, and F1;
- false-positive rate;
- event detection success;
- detection delay in timesteps.

The flagship PV false-data-injection scenario currently achieves `0.972` precision, recall,
and F1 with one-step delay. Gradual battery-efficiency loss is harder and intentionally
shows lower recall, which gives later work a meaningful improvement target.

## Limitations

- Calibration currently uses one clean simulated day; later evaluation should use multiple
  seeds, seasons, and operating conditions.
- Point-level evaluation counts persistent physical aftermath outside the configured attack
  window as false positives, even when the system remains physically divergent.
- Isolation Forest detects novelty but does not identify attack subtype.
- Thresholds are research-prototype defaults, not certified safety limits.

## Acceptance criteria

- Detector fitting is independent of scenario labels.
- Clean-baseline false detections remain low after persistence filtering.
- The flagship false-data attack is detected within two timesteps.
- The diagnosed component is the PV sensor for the flagship scenario.
- All catalog scenarios produce at least one detected event.
- Outputs include row-level evidence, event JSON, and reproducible evaluation metrics.
