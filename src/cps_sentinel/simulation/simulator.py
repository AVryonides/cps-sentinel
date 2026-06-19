"""Orchestration and metrics for the Phase 1 smart nanogrid simulator."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cps_sentinel.config import Settings
from cps_sentinel.simulation.battery import BatteryModel
from cps_sentinel.simulation.controller import dispatch_power
from cps_sentinel.simulation.profiles import generate_profiles


@dataclass(frozen=True)
class SimulationSummary:
    rows: int
    minimum_soc: float
    maximum_soc: float
    imported_energy_kwh: float
    exported_energy_kwh: float
    maximum_balance_error_kw: float


def run_simulation(settings: Settings) -> pd.DataFrame:
    """Run a deterministic nanogrid simulation from validated settings."""
    profiles = generate_profiles(settings)
    battery = BatteryModel(settings.simulation.battery)
    timestep_hours = settings.simulation.timestep_minutes / 60
    soc = settings.simulation.battery.initial_soc
    records: list[dict[str, object]] = []

    for timestamp, pv_kw_raw, load_kw_raw in profiles.itertuples(index=False, name=None):
        pv_kw = float(pv_kw_raw)
        load_kw = float(load_kw_raw)
        soc_start = soc
        decision = dispatch_power(pv_kw, load_kw, soc, timestep_hours, battery)
        soc = decision.next_soc
        balance_error_kw = pv_kw + decision.battery_power_kw + decision.grid_power_kw - load_kw
        records.append(
            {
                "timestamp": timestamp,
                "pv_kw": pv_kw,
                "load_kw": load_kw,
                "battery_soc_start": soc_start,
                "battery_soc": soc,
                "requested_battery_power_kw": decision.requested_battery_power_kw,
                "battery_power_kw": decision.battery_power_kw,
                "grid_power_kw": decision.grid_power_kw,
                "controller_action": decision.controller_action,
                "power_balance_error_kw": balance_error_kw,
                "system_state": _system_state(soc, settings),
            }
        )

    return pd.DataFrame.from_records(records)


def summarize_simulation(frame: pd.DataFrame, timestep_minutes: int) -> SimulationSummary:
    """Calculate compact physical and operational metrics for a completed run."""
    timestep_hours = timestep_minutes / 60
    grid = frame["grid_power_kw"]
    return SimulationSummary(
        rows=len(frame),
        minimum_soc=float(frame["battery_soc"].min()),
        maximum_soc=float(frame["battery_soc"].max()),
        imported_energy_kwh=float(grid.clip(lower=0).sum() * timestep_hours),
        exported_energy_kwh=float(-grid.clip(upper=0).sum() * timestep_hours),
        maximum_balance_error_kw=float(frame["power_balance_error_kw"].abs().max()),
    )


def _system_state(soc: float, settings: Settings) -> str:
    battery = settings.simulation.battery
    tolerance = 1e-8
    if soc <= battery.minimum_soc + tolerance:
        return "battery_at_minimum"
    if soc >= battery.maximum_soc - tolerance:
        return "battery_at_maximum"
    return "normal"
