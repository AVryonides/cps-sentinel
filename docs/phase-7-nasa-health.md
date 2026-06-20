# Phase 7: NASA battery health validation

## Purpose

Phase 7 adds a real-data prognostics track without pretending the NASA cells are measurements from
the simulated nanogrid. The track validates CPS Sentinel's ability to identify gradual physical
degradation and produce maintenance-oriented alerts alongside its security-monitoring capability.

## Dataset boundary

The canonical experiment uses NASA PCoE cells B0005, B0006, B0007, and B0018 at room temperature.
Only discharge cycles containing measured capacity are used for the baseline. The bundled NASA
documentation defines end of life as a 30% fade from 2.0 Ah to 1.4 Ah.

Raw archives and extracted MATLAB files remain Git-ignored. The repository records the source,
checksum, experiment group, cells, EOL definition, and required citation.

## Cycle-level contract

Each normalized record contains battery identity, discharge-cycle index, original operation index,
timestamp, ambient temperature, measured capacity, discharge duration, minimum terminal voltage,
and maximum measured temperature.

## Health and prognostics baseline

State of health is measured capacity divided by the 2.0 Ah rated capacity. Status is Healthy above
80%, Warning from 70% through 80%, and Critical at or below the NASA 70% EOL level.

RUL is projected from a conservative degradation rate: the larger of the recent rolling linear
capacity-loss slope and cumulative fade from the documented 2.0 Ah rated capacity. This physical
anchor prevents an early capacity plateau from producing an unbounded forecast. At cycle `n`, the
calculation uses only cycles up to and including `n`; future cycles are never used as model inputs.
Predictions are evaluated against the first observed cycle at or below 1.4 Ah using MAE and RMSE in
cycles. This is an interpretable baseline, not a claim of deployment-grade battery prognosis.

## Outputs

- Cycle-level CSV with SOH, health status, observed EOL, actual RUL, estimated RUL, and degradation
  rate.
- Latest-state JSON health alert per battery with physical impact and bounded maintenance guidance.
- Interactive capacity, SOH, and estimated-versus-observed RUL report.
