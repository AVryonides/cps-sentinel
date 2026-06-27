# CV-ready project summary

## Short description

Built CPS Sentinel, a digital-twin cyber-physical systems monitoring prototype for smart
nanogrids with attack/fault injection, hybrid anomaly detection, risk-ranked operator guidance,
external NASA battery-health validation, iTrust SWaT industrial-security validation, and a
NiceGUI explainability dashboard.

## CV bullet options

- Developed an end-to-end CPS monitoring prototype combining smart-nanogrid simulation,
  physics-aware digital-twin residuals, hybrid anomaly detection, and risk-ranked response
  recommendations.
- Implemented reproducible cyberattack/fault scenarios with labels withheld from detection and
  used only for post-hoc evaluation.
- Validated the framework across synthetic nanogrid incidents, NASA battery aging prognostics,
  and iTrust SWaT industrial attack-detection data while keeping restricted raw datasets outside
  version control.
- Built a NiceGUI operations dashboard that explains incidents in operator language, including
  evidence, physical impact, detector reasoning, risk score, and bounded response guidance.
- Added a reproducible demo workflow that regenerates local CSV, JSON, HTML, manifest, and
  markdown report artifacts with one CLI command.
- Added scenario benchmarking and operator-report export workflows, detecting events across all
  8 committed nanogrid scenarios with average F1 0.886.

## Suggested one-line CV entry

**CPS Sentinel:** Digital-twin CPS security and health monitoring prototype using Python,
NiceGUI, Plotly, scikit-learn, NASA battery data, and iTrust SWaT process data.

## Interview talking points

- Why the digital twin is kept independent from observed sensor values.
- How clean-data calibration avoids label leakage.
- Why event-level detection can be operationally useful even when point-level recall is imperfect.
- How the response layer is intentionally bounded as decision support, not autonomous actuation.
- How the project balances reproducibility with restricted dataset handling.
- How the scenario benchmark complements the flagship incident demo.
