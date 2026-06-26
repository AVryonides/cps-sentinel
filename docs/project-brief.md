# CPS Sentinel project brief

CPS Sentinel is an end-to-end cyber-physical systems monitoring prototype. It combines a
smart-nanogrid simulator, an independent physics-aware digital twin, attack/fault injection,
hybrid anomaly detection, risk scoring, operator guidance, external validation tracks, and a
NiceGUI dashboard.

## Problem

Cyber-physical systems can fail in ways that are hard to understand from raw telemetry alone.
A sensor attack, actuator fault, or degrading component may look like a normal operational
change until it affects physical behavior. CPS Sentinel addresses this by comparing observed
plant behavior with an independent expected-behavior model, then turning sustained deviations
into evidence-backed operator guidance.

## Implementation

The core demonstration uses a deterministic smart nanogrid with PV generation, load demand,
battery state of charge, and grid exchange. Attack and fault scenarios are injected into the
closed control loop while preserving ground-truth labels for evaluation only. The detector
combines robust physics thresholds, Isolation Forest novelty scoring, and temporal persistence
before aggregating alerts into events. A risk layer ranks incidents by confidence, measured
physical impact, duration, and proximity to configured operating limits.

External validation tracks extend the project beyond synthetic data:

- NASA battery aging data validates health monitoring and remaining-useful-life estimation.
- iTrust SWaT historian data validates industrial process attack detection without exposing
  restricted raw files.

## Current results

| Track | Result |
| --- | --- |
| Nanogrid attack demo | F1 0.972 and risk score 95.2/100 on the flagship PV false-data injection scenario |
| NASA battery health | 4 batteries, 636 discharge cycles, RUL MAE 8.99 cycles |
| SWaT industrial security | 5/6 scheduled attack events detected, point F1 0.446, false-positive rate 11.93% |

## Data and safety boundaries

The dashboard is decision support only. It does not send control commands or perform autonomous
actuation. Restricted raw datasets remain local and are excluded from Git. Public documentation
reports derived metrics and reproducible commands without redistributing protected data.

## Demo command

```bash
cps-sentinel demo \
  --config config/default.yaml \
  --output-dir reports/demo
```

The demo command regenerates the nanogrid evidence bundle and summarizes NASA/SWaT processed
results when they exist locally.
