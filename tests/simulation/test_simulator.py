from pathlib import Path

import pandas as pd

from cps_sentinel.config import load_settings
from cps_sentinel.simulation import run_simulation, summarize_simulation

ROOT = Path(__file__).resolve().parents[2]


def test_default_simulation_satisfies_physical_invariants() -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")
    frame = run_simulation(settings)
    battery = settings.simulation.battery

    assert len(frame) == 288
    assert (frame[["pv_kw", "load_kw"]] >= 0).all().all()
    assert frame["battery_soc"].between(battery.minimum_soc, battery.maximum_soc).all()
    assert frame["battery_power_kw"].abs().max() <= battery.maximum_power_kw
    assert frame["power_balance_error_kw"].abs().max() < 1e-9
    assert {"charge", "discharge", "import"}.issubset(set(frame["controller_action"]))


def test_default_simulation_is_reproducible() -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")

    pd.testing.assert_frame_equal(run_simulation(settings), run_simulation(settings))


def test_summary_reports_grid_energy_and_soc_range() -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")
    frame = run_simulation(settings)
    summary = summarize_simulation(frame, settings.simulation.timestep_minutes)

    assert summary.rows == 288
    assert summary.imported_energy_kwh > 0
    assert summary.exported_energy_kwh >= 0
    assert summary.minimum_soc >= settings.simulation.battery.minimum_soc
    assert summary.maximum_soc <= settings.simulation.battery.maximum_soc
