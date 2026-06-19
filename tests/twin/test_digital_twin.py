from pathlib import Path

import pandas as pd
import pytest

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin, summarize_twin

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def baseline() -> tuple[Settings, pd.DataFrame]:
    settings = load_settings(ROOT / "config" / "default.yaml")
    return settings, run_simulation(settings)


def test_twin_is_aligned_and_physically_valid(baseline: tuple[Settings, pd.DataFrame]) -> None:
    settings, observed = baseline
    frame = run_digital_twin(settings, observed)
    battery = settings.simulation.battery

    assert len(frame) == len(observed) == 288
    assert frame["expected_battery_soc"].between(battery.minimum_soc, battery.maximum_soc).all()
    assert frame["expected_battery_power_kw"].abs().max() <= battery.maximum_power_kw
    assert frame["twin_power_balance_error_kw"].abs().max() < 1e-9


def test_expected_trajectory_is_independent_of_observed_sensor_values(
    baseline: tuple[Settings, pd.DataFrame],
) -> None:
    settings, observed = baseline
    original = run_digital_twin(settings, observed)
    tampered = observed.copy()
    tampered.loc[100:110, "pv_kw"] += 5.0
    attacked = run_digital_twin(settings, tampered)

    pd.testing.assert_series_equal(original["expected_pv_kw"], attacked["expected_pv_kw"])
    pd.testing.assert_series_equal(
        original["expected_grid_power_kw"], attacked["expected_grid_power_kw"]
    )
    residual_change = (
        attacked.loc[100:110, "pv_residual_kw"] - original.loc[100:110, "pv_residual_kw"]
    )
    assert residual_change.to_numpy() == pytest.approx([5.0] * 11)


def test_residuals_follow_observed_minus_expected(
    baseline: tuple[Settings, pd.DataFrame],
) -> None:
    settings, observed = baseline
    frame = run_digital_twin(settings, observed)

    pd.testing.assert_series_equal(
        frame["grid_power_residual_kw"],
        frame["grid_power_kw"] - frame["expected_grid_power_kw"],
        check_names=False,
    )
    summary = summarize_twin(frame)
    assert summary.rows == 288
    assert summary.pv_mae_kw > 0
    assert summary.maximum_twin_balance_error_kw < 1e-9


def test_misaligned_observations_are_rejected(
    baseline: tuple[Settings, pd.DataFrame],
) -> None:
    settings, observed = baseline

    with pytest.raises(ValueError, match="align exactly"):
        run_digital_twin(settings, observed.iloc[:-1])
