"""Battery state transition model with explicit power and efficiency conventions."""

from __future__ import annotations

from dataclasses import dataclass

from cps_sentinel.config import BatteryConfig


@dataclass(frozen=True)
class BatteryStep:
    """Result of applying a requested battery power for one timestep."""

    requested_power_kw: float
    actual_power_kw: float
    next_soc: float

    @property
    def curtailed_power_kw(self) -> float:
        """Return requested minus delivered power with the configured sign convention."""
        return self.requested_power_kw - self.actual_power_kw


class BatteryModel:
    """Bounded energy-bucket model for control and CPS experiments.

    Battery power is positive when discharging to the electrical bus and negative when
    charging from the bus.
    """

    def __init__(self, config: BatteryConfig) -> None:
        self.config = config

    def step(self, requested_power_kw: float, soc: float, timestep_hours: float) -> BatteryStep:
        if timestep_hours <= 0:
            raise ValueError("timestep_hours must be positive")
        if not self.config.minimum_soc <= soc <= self.config.maximum_soc:
            raise ValueError("soc is outside configured battery limits")

        if requested_power_kw >= 0:
            energy_above_min_kwh = (soc - self.config.minimum_soc) * self.config.capacity_kwh
            energy_limited_power_kw = (
                energy_above_min_kwh * self.config.discharge_efficiency / timestep_hours
            )
            actual_power_kw = min(
                requested_power_kw,
                self.config.maximum_power_kw,
                energy_limited_power_kw,
            )
            energy_change_kwh = -(
                actual_power_kw * timestep_hours / self.config.discharge_efficiency
            )
        else:
            energy_headroom_kwh = (self.config.maximum_soc - soc) * self.config.capacity_kwh
            energy_limited_input_kw = energy_headroom_kwh / (
                self.config.charge_efficiency * timestep_hours
            )
            input_power_kw = min(
                -requested_power_kw,
                self.config.maximum_power_kw,
                energy_limited_input_kw,
            )
            actual_power_kw = -input_power_kw
            energy_change_kwh = input_power_kw * timestep_hours * self.config.charge_efficiency

        next_soc = soc + energy_change_kwh / self.config.capacity_kwh
        next_soc = min(self.config.maximum_soc, max(self.config.minimum_soc, next_soc))
        return BatteryStep(requested_power_kw, actual_power_kw, next_soc)
