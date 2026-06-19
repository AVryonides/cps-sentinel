from pathlib import Path

import pandas as pd
import pytest

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.scenarios import ScenarioKind, ScenarioSpec, ScenarioTarget, load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "config" / "scenarios"


@pytest.fixture
def settings() -> Settings:
    return load_settings(ROOT / "config" / "default.yaml")


def _run(settings: Settings, filename: str) -> pd.DataFrame:
    spec = load_scenario(SCENARIOS / filename, total_steps=288)
    return run_simulation(settings, spec)


def test_false_data_injection_changes_reported_not_true_pv(settings: Settings) -> None:
    frame = _run(settings, "pv-false-data-injection.yaml")
    active = frame[frame["scenario_active"]]
    normal = frame[~frame["scenario_active"]]

    assert len(active) == 36
    assert active["pv_kw"].to_numpy() == pytest.approx(active["true_pv_kw"] * 1.60)
    assert normal["pv_kw"].to_numpy() == pytest.approx(normal["true_pv_kw"])
    assert active["power_balance_error_kw"].abs().max() < 1e-9
    assert set(active["ground_truth_label"]) == {"attack"}


def test_sensor_freeze_holds_pre_event_value(settings: Settings) -> None:
    frame = _run(settings, "pv-sensor-freeze.yaml")
    active = frame[frame["scenario_active"]]

    assert active["pv_kw"].nunique() == 1
    assert active["pv_kw"].iloc[0] == pytest.approx(frame["true_pv_kw"].iloc[119])


def test_replay_attack_uses_offset_history(settings: Settings) -> None:
    frame = _run(settings, "pv-replay-attack.yaml")

    assert frame["pv_kw"].iloc[132] == pytest.approx(frame["true_pv_kw"].iloc[108])
    assert frame["pv_kw"].iloc[150] == pytest.approx(frame["true_pv_kw"].iloc[126])


def test_command_delay_delivers_historical_command(settings: Settings) -> None:
    frame = _run(settings, "battery-command-delay.yaml")

    assert frame["commanded_battery_power_kw"].iloc[108] == pytest.approx(
        frame["requested_battery_power_kw"].iloc[102]
    )
    assert frame["commanded_battery_power_kw"].iloc[140] == pytest.approx(
        frame["requested_battery_power_kw"].iloc[134]
    )


def test_actuator_manipulation_scales_command(settings: Settings) -> None:
    frame = _run(settings, "battery-actuator-manipulation.yaml")
    active = frame[frame["scenario_active"]]

    assert active["commanded_battery_power_kw"].to_numpy() == pytest.approx(
        active["requested_battery_power_kw"] * 1.75
    )


def test_noise_fault_is_reproducible(settings: Settings) -> None:
    first = _run(settings, "pv-sensor-noise-fault.yaml")
    second = _run(settings, "pv-sensor-noise-fault.yaml")

    pd.testing.assert_series_equal(first["pv_kw"], second["pv_kw"])
    assert set(first.loc[first["scenario_active"], "ground_truth_label"]) == {"fault"}


def test_sensor_failure_reports_zero(settings: Settings) -> None:
    frame = _run(settings, "pv-sensor-failure.yaml")

    assert (frame.loc[frame["scenario_active"], "pv_kw"] == 0).all()


def test_battery_efficiency_loss_changes_effective_parameters(settings: Settings) -> None:
    frame = _run(settings, "battery-efficiency-loss.yaml")
    active = frame[frame["scenario_active"]]
    normal = frame[~frame["scenario_active"]]

    assert active["effective_charge_efficiency"].min() == pytest.approx(0.7125)
    assert active["effective_charge_efficiency"].max() == pytest.approx(0.7125)
    assert normal["effective_charge_efficiency"].min() == pytest.approx(0.95)
    assert normal["effective_charge_efficiency"].max() == pytest.approx(0.95)


def test_twin_stays_independent_during_attack(settings: Settings) -> None:
    spec = load_scenario(SCENARIOS / "pv-false-data-injection.yaml", total_steps=288)
    attacked = run_digital_twin(settings, run_simulation(settings, spec))
    normal = run_digital_twin(settings, run_simulation(settings))

    pd.testing.assert_series_equal(attacked["expected_pv_kw"], normal["expected_pv_kw"])
    assert attacked.loc[attacked["scenario_active"], "pv_residual_kw"].abs().mean() > 1.0


def test_invalid_target_combination_is_rejected() -> None:
    spec = ScenarioSpec(
        name="invalid",
        kind=ScenarioKind.FALSE_DATA_INJECTION,
        target=ScenarioTarget.BATTERY,
        start_step=1,
        duration_steps=2,
        intensity=0.5,
    )

    with pytest.raises(ValueError, match="sensor target"):
        spec.validate(10)
