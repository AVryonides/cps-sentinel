import pytest

from cps_sentinel.config import BatteryConfig
from cps_sentinel.simulation.battery import BatteryModel
from cps_sentinel.simulation.controller import dispatch_power


def _battery() -> BatteryModel:
    return BatteryModel(BatteryConfig(10.0, 0.5, 0.1, 0.9, 5.0, 1.0, 1.0))


def test_deficit_is_supplied_by_battery() -> None:
    decision = dispatch_power(1.0, 4.0, 0.5, 1.0, _battery())

    assert decision.battery_power_kw == 3.0
    assert decision.grid_power_kw == 0.0
    assert decision.controller_action == "discharge"


def test_surplus_charges_battery_and_exports_remainder() -> None:
    decision = dispatch_power(8.0, 1.0, 0.89, 1.0, _battery())

    assert decision.battery_power_kw < 0
    assert decision.grid_power_kw < 0
    assert decision.controller_action == "charge_and_export"
    assert 8.0 + decision.battery_power_kw + decision.grid_power_kw - 1.0 == pytest.approx(0)
