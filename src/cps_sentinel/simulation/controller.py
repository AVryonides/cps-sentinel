"""Rule-based energy-management controller for the Phase 1 nanogrid."""

from __future__ import annotations

from dataclasses import dataclass

from cps_sentinel.simulation.battery import BatteryModel


@dataclass(frozen=True)
class DispatchDecision:
    requested_battery_power_kw: float
    battery_power_kw: float
    grid_power_kw: float
    next_soc: float
    controller_action: str


def dispatch_power(
    pv_kw: float,
    load_kw: float,
    soc: float,
    timestep_hours: float,
    battery: BatteryModel,
) -> DispatchDecision:
    """Balance net demand with the battery first and the grid second.

    Grid power is positive for import and negative for export. Battery power is positive
    for discharge and negative for charge.
    """
    if pv_kw < 0 or load_kw < 0:
        raise ValueError("pv_kw and load_kw cannot be negative")

    net_demand_kw = load_kw - pv_kw
    battery_step = battery.step(net_demand_kw, soc, timestep_hours)
    grid_power_kw = net_demand_kw - battery_step.actual_power_kw
    return DispatchDecision(
        requested_battery_power_kw=net_demand_kw,
        battery_power_kw=battery_step.actual_power_kw,
        grid_power_kw=grid_power_kw,
        next_soc=battery_step.next_soc,
        controller_action=_classify_action(battery_step.actual_power_kw, grid_power_kw),
    )


def _classify_action(battery_power_kw: float, grid_power_kw: float) -> str:
    tolerance = 1e-9
    if battery_power_kw > tolerance and grid_power_kw > tolerance:
        return "discharge_and_import"
    if battery_power_kw > tolerance:
        return "discharge"
    if battery_power_kw < -tolerance and grid_power_kw < -tolerance:
        return "charge_and_export"
    if battery_power_kw < -tolerance:
        return "charge"
    if grid_power_kw > tolerance:
        return "import"
    if grid_power_kw < -tolerance:
        return "export"
    return "balanced"
