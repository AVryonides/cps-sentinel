# Phase 3 - Closed-loop attack and fault injection

## High-level purpose

Phase 3 turns the normal nanogrid into an experimental cyber-physical system. Reproducible
scenarios can now corrupt sensing, delay or manipulate commands, and degrade physical
battery parameters while retaining exact ground truth.

These are not post-processing edits. Each scenario is injected before the controller or
physical state transition, so it can cause a genuine downstream consequence.

## Closed-loop execution order

Every simulation step follows this sequence:

1. Generate true PV and load conditions.
2. Apply an active sensor attack or fault to reported measurements.
3. Calculate the controller's nominal battery command from reported measurements.
4. Apply command delay or actuator manipulation when active.
5. Apply temporary physical battery degradation when active.
6. Enforce battery power, efficiency, capacity, and SOC constraints.
7. Let the grid close the balance using true physical PV and load.
8. Run the independent digital twin and calculate residuals.
9. Attach scenario timing and ground-truth labels.

## Supported scenarios

| Kind | Target | Effect |
| --- | --- | --- |
| `false_data_injection` | PV/load sensor | Scales the reported measurement |
| `sensor_freeze` | PV/load sensor | Holds the pre-event value |
| `replay_attack` | PV/load sensor | Replays a previous true measurement |
| `command_delay` | Battery command | Delivers an older controller command |
| `actuator_manipulation` | Battery command | Scales the command before actuation |
| `sensor_noise` | PV/load sensor | Adds seeded Gaussian measurement noise |
| `sensor_failure` | PV/load sensor | Reports zero during the fault |
| `battery_efficiency_loss` | Battery | Reduces charge/discharge efficiency |
| `battery_capacity_loss` | Battery | Reduces accessible capacity |

Attack scenarios are labeled `attack`; degradation and accidental sensor scenarios are
labeled `fault`.

## Scenario definition

Scenarios are version-controlled YAML files. A typical false-data-injection scenario is:

```yaml
name: PV sensor false-data injection
kind: false_data_injection
target: pv_sensor
start_step: 120
duration_steps: 36
intensity: 0.60
```

At five-minute resolution, this starts at 10:00 and remains active for three hours. The PV
sensor reports `true_pv * 1.60`, while the digital twin remains independent.

## Output and ground truth

Each labeled row contains:

- true and reported PV/load values;
- nominal, delivered, and physically achieved battery power;
- actual grid power and battery SOC;
- expected twin values and residuals;
- active scenario name, kind, target, intensity, and attack/fault label.

This makes later event-level precision, recall, false-positive rate, and detection-delay
metrics possible without reconstructing labels after the experiment.

## Acceptance criteria

- Scenario runs remain deterministic for fixed seeds and YAML definitions.
- The active row count exactly equals `duration_steps`.
- Physical power balance remains below `1e-9 kW` during attacks and faults.
- Sensor attacks change reported values without changing true environmental values.
- Command attacks change the delivered command inside the labeled window.
- Twin expected values remain independent of attacked observations.
- Invalid target/kind combinations and out-of-range windows fail before simulation.
