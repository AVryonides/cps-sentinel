# Phase 9: Unified operations interface

## Goal

Phase 9 brings the three CPS Sentinel evidence tracks into one NiceGUI application:

1. the simulated nanogrid, digital twin, hybrid detector, and risk response;
2. NASA battery degradation and remaining-useful-life validation;
3. iTrust SWaT industrial attack-detection validation.

The tracks share presentation conventions and explainability principles without pretending to
represent one physical plant.

## Product boundary

The web layer does not retrain models and does not contain duplicate simulation or detection
logic. The nanogrid view calls the production scenario pipeline. External validation views read
only generated files under `data/processed/`.

Raw NASA and SWaT source files are never served, embedded in charts, or exposed through the web
application. This is especially important for SWaT because iTrust prohibits redistribution.

## Interface modes

### Nanogrid monitor

Preserves the complete simulation-to-response reasoning chain: incident summary, sensor evidence,
physical consequence, detection logic, and bounded operator guidance.

### Battery health

Displays measured capacity, state of health, causal RUL estimates, forecast error, and the latest
maintenance priorities for each validated NASA cell.

### SWaT security

Displays point and event metrics, anomaly evidence aligned with withheld labels, leading affected
process tags, and bounded investigation actions. The view activates only after an authorized local
Phase 8 run generates `data/processed/swat-security.csv`.

## Availability behavior

Each external view has three explicit states:

- `ready`: a structurally valid processed result was loaded;
- `not_ready`: no generated result exists and the required command is shown;
- `error`: a result exists but does not satisfy the expected data contract.

The interface never substitutes synthetic metrics for a missing real-data result.

## Run locally

```bash
source .venv/bin/activate
python app/nicegui_app.py
```

Open `http://127.0.0.1:8080` and select a track from the left navigation.

## Acceptance criteria

- All three tracks are reachable from visible desktop and mobile navigation.
- The nanogrid scenario selector and reasoning chain remain functional.
- NASA and SWaT views use production-generated processed outputs.
- Missing and malformed external outputs produce explanatory states rather than blank pages.
- Raw restricted data is never read or exposed by the NiceGUI layer.
- Framework-neutral loaders and figure builders are tested independently of NiceGUI.
