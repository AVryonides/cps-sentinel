# Phase 11: reproducible demo workflow

## Goal

Phase 11 adds a single local command that regenerates a polished demo bundle for the project. The
bundle is designed for interviews, GitHub walkthroughs, and repeatable testing without manually
running several phase commands.

## Command

```bash
cps-sentinel demo \
  --config config/default.yaml \
  --output-dir reports/demo
```

The command always regenerates the flagship nanogrid attack/fault demo. It also summarizes NASA
and SWaT validation tracks if their processed local outputs already exist.

## Generated artifacts

The demo command writes local generated files under `reports/demo/`:

- `demo-summary.md` - human-readable walkthrough report;
- `demo-manifest.json` - machine-readable artifact manifest;
- `nanogrid-detection.csv` - row-level flagship detection output;
- `nanogrid-events.json` - aggregated detection events;
- `nanogrid-alerts.json` - risk-ranked operator alerts;
- `nanogrid-detection.html` - interactive detection report;
- `nanogrid-risk.html` - interactive risk-response report;
- optional NASA and SWaT HTML reports when processed local CSVs are available.

`reports/demo/` is ignored by Git because it is generated and may contain local validation results.

## Data boundary

The demo command does not read restricted raw datasets directly, except through existing processed
result paths supplied by the user. If NASA or SWaT processed outputs are missing, the report records
the command needed to generate them locally.

Raw NASA and iTrust/SWaT files remain outside Git and outside the generated demo report.

## Acceptance criteria

- One CLI command regenerates the main nanogrid demo artifacts.
- Missing external validation outputs produce helpful next steps instead of failures.
- Generated demo artifacts are ignored by Git.
- The report is useful to a reader without requiring command-line archaeology.
- Tests, linting, type checking, and CI remain green.
