import pytest

from cps_sentinel.config import BatteryConfig
from cps_sentinel.simulation.battery import BatteryModel


@pytest.fixture
def battery() -> BatteryModel:
    return BatteryModel(
        BatteryConfig(
            capacity_kwh=10.0,
            initial_soc=0.5,
            minimum_soc=0.1,
            maximum_soc=0.9,
            maximum_power_kw=5.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.90,
        )
    )


def test_discharge_accounts_for_efficiency(battery: BatteryModel) -> None:
    step = battery.step(requested_power_kw=2.0, soc=0.5, timestep_hours=0.5)

    assert step.actual_power_kw == 2.0
    assert step.next_soc == pytest.approx(0.5 - (2.0 * 0.5 / 0.90) / 10.0)


def test_charge_accounts_for_efficiency(battery: BatteryModel) -> None:
    step = battery.step(requested_power_kw=-2.0, soc=0.5, timestep_hours=0.5)

    assert step.actual_power_kw == -2.0
    assert step.next_soc == pytest.approx(0.5 + (2.0 * 0.5 * 0.95) / 10.0)


def test_power_and_soc_are_clipped_at_physical_limits(battery: BatteryModel) -> None:
    discharge = battery.step(requested_power_kw=20.0, soc=0.11, timestep_hours=1.0)
    charge = battery.step(requested_power_kw=-20.0, soc=0.89, timestep_hours=1.0)

    assert discharge.next_soc == pytest.approx(0.1)
    assert discharge.actual_power_kw == pytest.approx(0.09)
    assert charge.next_soc == pytest.approx(0.9)
    assert charge.actual_power_kw == pytest.approx(-(0.1 / 0.95))
