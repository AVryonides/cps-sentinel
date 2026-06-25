# Phase 10: dashboard polish and explainability

## Goal

Phase 10 turns the NiceGUI interface into a demo-ready operations dashboard. The emphasis is not
more algorithms; it is clearer communication of the evidence chain:

1. what the system is monitoring;
2. what evidence caused an alert;
3. what the metrics mean;
4. what action is recommended;
5. what the safety and data boundaries are.

## Design principles

- Avoid raw “model output” presentation when a plain-language interpretation is possible.
- Explain metrics beside the values so non-specialists can read the dashboard.
- Keep the cyber-physical boundary visible: the dashboard recommends checks but never actuates.
- Keep the data boundary visible: restricted NASA and iTrust raw files stay local and out of Git.
- Prefer event-level storytelling over overwhelming the user with unexplained charts.

## Implemented polish

- Added a clearer hero area for the nanogrid, NASA health, and SWaT validation tracks.
- Added reusable explanation cards for evidence, reasoning, decision, and data-boundary concepts.
- Added metric help cards for risk score, detection delay, SOH, RUL error, F1, event recall, and
  false-positive rate.
- Added “What this means operationally” summaries before dense figures.
- Improved external-track empty states with step-by-step local generation guidance.
- Updated the dashboard header and sidebar language for the unified Phase 10 interface.

## Acceptance criteria

- The dashboard tells a coherent story before the user interprets charts.
- A reader without CPS expertise can understand the major metrics.
- SWaT and NASA views clearly state that raw datasets remain local.
- Existing tests, formatting, type checks, and CI stay green.
