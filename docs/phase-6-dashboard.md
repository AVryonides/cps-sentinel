# Phase 6: Interactive mission-control dashboard

## Goal

Phase 6 turns the simulation, digital twin, detection engine, and risk layer into a coherent
portfolio demonstration. A user selects any catalogued attack or fault and sees the entire CPS
reasoning chain without running separate commands.

## User journey

1. Select a deterministic scenario in the sidebar.
2. Inspect physical, reported, and digital-twin values in the System Overview.
3. Examine residual magnitudes and independent expected behavior in Digital Twin.
4. Review physics, statistical, and temporal evidence in Detection Engine.
5. Read the prioritized physical-impact summary and bounded response in Alert & Response.

## Technical boundary

The NiceGUI dashboard calls the same production modules and configuration as the CLI. It does not
contain a second implementation of the simulator, twin, detector, or risk score. Framework-neutral
analysis and Plotly builders live in `cps_sentinel.dashboard`, while NiceGUI is responsible only for
layout and interaction. Cached deterministic runs avoid recomputing previously selected scenarios.
Scenario labels remain excluded from detector and risk inputs and are visible only in retrospective
evaluation.

The interface uses a persistent desktop drawer and a visible mobile menu control. Explanatory
reading guides precede technical charts, event windows are shaded consistently, and the quick
reference defines CPS terminology for non-specialist readers.

## Run locally

```bash
source .venv/bin/activate
python app/nicegui_app.py
```

The default server is available at `http://localhost:8080`.
