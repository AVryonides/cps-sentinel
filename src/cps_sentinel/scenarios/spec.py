"""Validated scenario definitions and YAML loading."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class ScenarioKind(StrEnum):
    FALSE_DATA_INJECTION = "false_data_injection"
    SENSOR_FREEZE = "sensor_freeze"
    REPLAY_ATTACK = "replay_attack"
    COMMAND_DELAY = "command_delay"
    ACTUATOR_MANIPULATION = "actuator_manipulation"
    SENSOR_NOISE = "sensor_noise"
    SENSOR_FAILURE = "sensor_failure"
    BATTERY_EFFICIENCY_LOSS = "battery_efficiency_loss"
    BATTERY_CAPACITY_LOSS = "battery_capacity_loss"


class ScenarioTarget(StrEnum):
    PV_SENSOR = "pv_sensor"
    LOAD_SENSOR = "load_sensor"
    BATTERY_COMMAND = "battery_command"
    BATTERY = "battery"


ATTACK_KINDS = {
    ScenarioKind.FALSE_DATA_INJECTION,
    ScenarioKind.SENSOR_FREEZE,
    ScenarioKind.REPLAY_ATTACK,
    ScenarioKind.COMMAND_DELAY,
    ScenarioKind.ACTUATOR_MANIPULATION,
}
SENSOR_KINDS = {
    ScenarioKind.FALSE_DATA_INJECTION,
    ScenarioKind.SENSOR_FREEZE,
    ScenarioKind.REPLAY_ATTACK,
    ScenarioKind.SENSOR_NOISE,
    ScenarioKind.SENSOR_FAILURE,
}
BATTERY_FAULT_KINDS = {
    ScenarioKind.BATTERY_EFFICIENCY_LOSS,
    ScenarioKind.BATTERY_CAPACITY_LOSS,
}


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    kind: ScenarioKind
    target: ScenarioTarget
    start_step: int
    duration_steps: int
    intensity: float = 0.0
    delay_steps: int = 0
    replay_offset_steps: int = 0
    seed: int = 42

    @property
    def end_step(self) -> int:
        return self.start_step + self.duration_steps

    @property
    def ground_truth_label(self) -> str:
        return "attack" if self.kind in ATTACK_KINDS else "fault"

    def active(self, step: int) -> bool:
        return self.start_step <= step < self.end_step

    def validate(self, total_steps: int | None = None) -> None:
        if not self.name.strip():
            raise ValueError("Scenario name cannot be empty")
        if self.start_step < 0 or self.duration_steps <= 0:
            raise ValueError("Scenario start must be non-negative and duration must be positive")
        if total_steps is not None and self.end_step > total_steps:
            raise ValueError("Scenario window exceeds the configured simulation")
        if self.kind in SENSOR_KINDS and self.target not in {
            ScenarioTarget.PV_SENSOR,
            ScenarioTarget.LOAD_SENSOR,
        }:
            raise ValueError(f"{self.kind.value} requires a sensor target")
        if self.kind in {ScenarioKind.COMMAND_DELAY, ScenarioKind.ACTUATOR_MANIPULATION} and (
            self.target is not ScenarioTarget.BATTERY_COMMAND
        ):
            raise ValueError(f"{self.kind.value} requires battery_command target")
        if self.kind in BATTERY_FAULT_KINDS and self.target is not ScenarioTarget.BATTERY:
            raise ValueError(f"{self.kind.value} requires battery target")
        if self.kind is ScenarioKind.COMMAND_DELAY and self.delay_steps <= 0:
            raise ValueError("command_delay requires delay_steps > 0")
        if self.kind is ScenarioKind.REPLAY_ATTACK and self.replay_offset_steps <= 0:
            raise ValueError("replay_attack requires replay_offset_steps > 0")
        if self.kind in BATTERY_FAULT_KINDS and not 0 < self.intensity < 1:
            raise ValueError("Battery loss intensity must be between 0 and 1")
        if self.kind is ScenarioKind.SENSOR_NOISE and self.intensity <= 0:
            raise ValueError("sensor_noise intensity must be positive")
        if self.kind is ScenarioKind.ACTUATOR_MANIPULATION and self.intensity <= -1:
            raise ValueError("actuator manipulation intensity must be greater than -1")


def load_scenario(path: str | Path, total_steps: int | None = None) -> ScenarioSpec:
    """Load and validate a scenario from a YAML file."""
    scenario_path = Path(path)
    if not scenario_path.is_file():
        raise ValueError(f"Scenario file not found: {scenario_path}")
    raw = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Scenario root must be a mapping")
    spec = _from_mapping(raw)
    spec.validate(total_steps)
    return spec


def _from_mapping(raw: dict[str, Any]) -> ScenarioSpec:
    try:
        return ScenarioSpec(
            name=str(raw["name"]),
            kind=ScenarioKind(str(raw["kind"])),
            target=ScenarioTarget(str(raw["target"])),
            start_step=int(raw["start_step"]),
            duration_steps=int(raw["duration_steps"]),
            intensity=float(raw.get("intensity", 0.0)),
            delay_steps=int(raw.get("delay_steps", 0)),
            replay_offset_steps=int(raw.get("replay_offset_steps", 0)),
            seed=int(raw.get("seed", 42)),
        )
    except KeyError as exc:
        raise ValueError(f"Scenario is missing required field: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid scenario configuration: {exc}") from exc
