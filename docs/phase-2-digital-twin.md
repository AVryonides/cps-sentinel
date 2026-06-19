# Phase 2 - Independent digital twin

## High-level purpose

The physical simulator answers: "What happened in the nanogrid?" The digital twin answers:
"What should have happened according to an independent model?"

The difference between those answers is evidence. Small residuals represent ordinary
profile variability and model mismatch. Later phases will inject attacks and faults that
should create larger, structured residuals.

## Independence boundary

The twin does not consume observed PV, load, battery, or grid values to produce its expected
trajectory. It uses only:

- the configured timeline;
- deterministic time-based PV and load reference profiles;
- battery parameters and initial SOC;
- its own battery state transitions;
- the shared, documented controller policy.

Observed values enter only after the expected trajectory has been calculated. This prevents
an attacked sensor from corrupting both sides of the comparison identically.

## Expected trajectory

The twin generates noise-free reference PV and load profiles. It then applies the Phase 1
battery equations, SOC limits, efficiency losses, power limits, and controller policy to
produce:

- expected PV and load;
- expected requested and delivered battery power;
- expected grid import/export;
- expected start- and end-of-step SOC;
- expected controller action and system state.

The twin satisfies the same power balance as the physical simulator:

```text
expected_pv + expected_battery + expected_grid - expected_load = 0
```

## Residual contract

All residuals use the same sign convention:

```text
residual = observed - expected
```

The output includes PV, load, battery-power, grid-power, and battery-SOC residuals, plus a
boolean indicating whether the observed and expected controller actions agree.

Phase 2 does not label residuals as attacks. Thresholding, event classification, and alert
generation belong to later detection phases.

## Acceptance criteria

- The expected trajectory contains the same timestamps and row count as the observation.
- Expected behavior is deterministic for a fixed configuration.
- The twin power-balance error remains below `1e-9 kW`.
- Expected SOC and battery power remain within configured limits.
- Changing an observed sensor value changes its residual but not the expected trajectory.
- Misaligned or incomplete observation frames are rejected clearly.
