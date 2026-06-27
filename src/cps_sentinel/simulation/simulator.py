"""Orchestration and metrics for the smart nanogrid simulator."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cps_sentinel.config import Settings
from cps_sentinel.scenarios import ScenarioRuntime, ScenarioSpec
from cps_sentinel.simulation.battery import BatteryModel
from cps_sentinel.simulation.controller import classify_action
from cps_sentinel.simulation.profiles import generate_profiles


@dataclass(frozen=True)
class SimulationSummary:
    rows: int
    minimum_soc: float
    maximum_soc: float
    imported_energy_kwh: float
    exported_energy_kwh: float
    maximum_balance_error_kw: float


def run_simulation(settings: Settings, scenario: ScenarioSpec | None = None) -> pd.DataFrame:
    """Run a deterministic nanogrid simulation from validated settings."""
    return simulate_profiles(settings, generate_profiles(settings), scenario)


def simulate_profiles(
    settings: Settings,
    profiles: pd.DataFrame,
    scenario: ScenarioSpec | None = None,
) -> pd.DataFrame:
    """Apply the nanogrid physics and controller to an aligned profile frame."""
    required_columns = {"timestamp", "pv_kw", "load_kw"}
    missing = required_columns.difference(profiles.columns)
    if missing:
        raise ValueError(f"Profile frame is missing columns: {sorted(missing)}")

    if scenario:
        scenario.validate(len(profiles))
    runtime = ScenarioRuntime(scenario)
    timestep_hours = settings.simulation.timestep_minutes / 60
    soc = settings.simulation.battery.initial_soc
    records: list[dict[str, object]] = []

    for step, (timestamp, pv_kw_raw, load_kw_raw) in enumerate(
        profiles.itertuples(index=False, name=None)
    ):
        true_pv_kw = float(pv_kw_raw)
        true_load_kw = float(load_kw_raw)
        pv_kw, load_kw = runtime.sensor_values(step, true_pv_kw, true_load_kw)
        soc_start = soc
        nominal_command_kw = load_kw - pv_kw
        commanded_power_kw = runtime.battery_command(step, nominal_command_kw)
        effective_battery_config = runtime.battery_config(step, settings.simulation.battery)
        battery_step = BatteryModel(effective_battery_config).step(
            commanded_power_kw, soc, timestep_hours
        )
        soc = battery_step.next_soc
        grid_power_kw = true_load_kw - true_pv_kw - battery_step.actual_power_kw
        balance_error_kw = true_pv_kw + battery_step.actual_power_kw + grid_power_kw - true_load_kw
        measurement_balance_error_kw = (
            pv_kw + battery_step.actual_power_kw + grid_power_kw - load_kw
        )
        metadata = runtime.metadata(step)
        records.append(
            {
                "timestamp": timestamp,
                "true_pv_kw": true_pv_kw,
                "true_load_kw": true_load_kw,
                "pv_kw": pv_kw,
                "load_kw": load_kw,
                "battery_soc_start": soc_start,
                "battery_soc": soc,
                "requested_battery_power_kw": nominal_command_kw,
                "commanded_battery_power_kw": commanded_power_kw,
                "battery_power_kw": battery_step.actual_power_kw,
                "grid_power_kw": grid_power_kw,
                "controller_action": classify_action(battery_step.actual_power_kw, grid_power_kw),
                "power_balance_error_kw": balance_error_kw,
                "measurement_balance_error_kw": measurement_balance_error_kw,
                "system_state": _system_state(soc, settings),
                "effective_battery_capacity_kwh": effective_battery_config.capacity_kwh,
                "effective_charge_efficiency": effective_battery_config.charge_efficiency,
                "effective_discharge_efficiency": effective_battery_config.discharge_efficiency,
                **metadata,
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
