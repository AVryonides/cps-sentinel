"""Stateful closed-loop application of attack and fault scenarios."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from cps_sentinel.config import BatteryConfig
from cps_sentinel.scenarios.spec import ScenarioKind, ScenarioSpec, ScenarioTarget


class ScenarioRuntime:
    """Apply one validated scenario while retaining the history it requires."""

    def __init__(self, spec: ScenarioSpec | None) -> None:
        self.spec = spec
        self._rng = np.random.default_rng(spec.seed if spec else 0)
        self._true_pv_history: list[float] = []
        self._true_load_history: list[float] = []
        self._nominal_command_history: list[float] = []

    def sensor_values(
        self, step: int, true_pv_kw: float, true_load_kw: float
    ) -> tuple[float, float]:
        pv_kw = true_pv_kw
        load_kw = true_load_kw
        spec = self.spec
        if (
            spec
            and spec.active(step)
            and spec.kind
            in {
                ScenarioKind.FALSE_DATA_INJECTION,
                ScenarioKind.SENSOR_FREEZE,
                ScenarioKind.REPLAY_ATTACK,
                ScenarioKind.SENSOR_NOISE,
                ScenarioKind.SENSOR_FAILURE,
            }
        ):
            if spec.target is ScenarioTarget.PV_SENSOR:
                pv_kw = self._modify_sensor(step, true_pv_kw, self._true_pv_history)
            else:
                load_kw = self._modify_sensor(step, true_load_kw, self._true_load_history)

        self._true_pv_history.append(true_pv_kw)
        self._true_load_history.append(true_load_kw)
        return max(0.0, pv_kw), max(0.0, load_kw)

    def battery_command(self, step: int, nominal_command_kw: float) -> float:
        command_kw = nominal_command_kw
        spec = self.spec
        if spec and spec.active(step):
            if spec.kind is ScenarioKind.COMMAND_DELAY:
                history_index = len(self._nominal_command_history) - spec.delay_steps
                command_kw = (
                    self._nominal_command_history[history_index] if history_index >= 0 else 0.0
                )
            elif spec.kind is ScenarioKind.ACTUATOR_MANIPULATION:
                command_kw = nominal_command_kw * (1 + spec.intensity)
        self._nominal_command_history.append(nominal_command_kw)
        return command_kw

    def battery_config(self, step: int, base: BatteryConfig) -> BatteryConfig:
        spec = self.spec
        if not spec or not spec.active(step):
            return base
        if spec.kind is ScenarioKind.BATTERY_EFFICIENCY_LOSS:
            factor = 1 - spec.intensity
            return replace(
                base,
                charge_efficiency=base.charge_efficiency * factor,
                discharge_efficiency=base.discharge_efficiency * factor,
            )
        if spec.kind is ScenarioKind.BATTERY_CAPACITY_LOSS:
            return replace(base, capacity_kwh=base.capacity_kwh * (1 - spec.intensity))
        return base

    def metadata(self, step: int) -> dict[str, object]:
        spec = self.spec
        active = bool(spec and spec.active(step))
        return {
            "scenario_active": active,
            "scenario_name": spec.name if active and spec else "normal",
            "scenario_kind": spec.kind.value if active and spec else "normal",
            "scenario_target": spec.target.value if active and spec else "none",
            "ground_truth_label": spec.ground_truth_label if active and spec else "normal",
            "scenario_intensity": spec.intensity if active and spec else 0.0,
        }

    def _modify_sensor(self, step: int, current: float, history: list[float]) -> float:
        assert self.spec is not None
        spec = self.spec
        if spec.kind is ScenarioKind.FALSE_DATA_INJECTION:
            return current * (1 + spec.intensity)
        if spec.kind is ScenarioKind.SENSOR_FREEZE:
            freeze_index = max(0, spec.start_step - 1)
            return history[freeze_index] if history else current
        if spec.kind is ScenarioKind.REPLAY_ATTACK:
            replay_index = step - spec.replay_offset_steps
            return history[replay_index] if 0 <= replay_index < len(history) else current
        if spec.kind is ScenarioKind.SENSOR_NOISE:
            return current + float(self._rng.normal(0, spec.intensity))
        if spec.kind is ScenarioKind.SENSOR_FAILURE:
            return 0.0
        return current
