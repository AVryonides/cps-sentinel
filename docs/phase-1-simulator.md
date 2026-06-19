# Phase 1 - Smart nanogrid simulator

## Scope

The Phase 1 simulator is a deterministic, discrete-time model of a grid-connected nanogrid
containing PV generation, electrical load, a battery, an energy-management controller, and
an unconstrained utility-grid connection.

It is intentionally transparent. Its purpose is to create physically consistent normal
behavior for later digital-twin, attack, fault, and detection experiments.

## Sign conventions

| Variable | Positive | Negative |
| --- | --- | --- |
| `battery_power_kw` | Battery discharging to the bus | Battery charging from the bus |
| `grid_power_kw` | Grid import | Grid export |

Every timestep satisfies the power balance:

```text
pv_kw + battery_power_kw + grid_power_kw - load_kw = 0
```

## Battery state transition

For discharge power `P_b > 0`:

```text
E_next = E_now - P_b * dt / discharge_efficiency
```

For charging power `P_b < 0`:

```text
E_next = E_now + (-P_b) * dt * charge_efficiency
```

The battery model limits requested power using maximum charge/discharge power, available
energy above minimum SOC, and remaining headroom below maximum SOC.

## Controller policy

The controller calculates net demand as `load_kw - pv_kw`.

1. When net demand is positive, it requests battery discharge and imports any remainder.
2. When net demand is negative, it requests battery charging and exports any remainder.
3. The battery model clips requests to physically feasible power.
4. The grid closes the remaining power balance.

This simple policy gives later phases a clear baseline whose decisions can be corrupted,
delayed, replayed, or compared against an independent digital twin.

## Output contract

The simulation CSV contains:

- timestamp and environmental profiles;
- start- and end-of-step battery SOC;
- requested and delivered battery power;
- grid import/export power;
- controller action;
- power-balance error;
- high-level system state.

The CLI can also write a self-contained interactive HTML report with synchronized plots for
PV and load, battery and grid power, and battery state of charge.

## Acceptance criteria

- A 24-hour, five-minute simulation contains 288 rows.
- Identical configuration and seed produce identical output.
- PV and load never become negative.
- SOC never leaves its configured interval.
- Battery power never exceeds its configured rating.
- The absolute power-balance error remains below `1e-9 kW`.
