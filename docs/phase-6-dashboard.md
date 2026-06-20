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

The dashboard calls the same production modules and configuration as the CLI. It does not contain
a second implementation of the simulator, twin, detector, or risk score. Streamlit caching avoids
recomputing a scenario after tab changes. Scenario labels remain excluded from detector and risk
inputs and are visible only in retrospective evaluation charts and metrics.

## Run locally

```bash
source .venv/bin/activate
streamlit run app/streamlit_app.py
```

The default server is available at `http://localhost:8501`.
