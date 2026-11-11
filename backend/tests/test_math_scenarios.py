"""Additional edge-case tests for scenario inputs."""

import pytest

from app.analytics.scenarios import (
    cancellation_reduction_scenario,
    order_recovery_scenario,
    revenue_recovery_scenario,
)


def test_scenario_rejects_invalid_values():
    with pytest.raises(ValueError):
        order_recovery_scenario(-1, 10, 100)
    with pytest.raises(ValueError):
        order_recovery_scenario(10, 501, 100)
    with pytest.raises(ValueError):
        cancellation_reduction_scenario(0, 0, 5, 100)
    with pytest.raises(ValueError):
        revenue_recovery_scenario(-1, 100)


def test_scenario_does_not_invent_revenue_when_average_is_missing():
    result = order_recovery_scenario(10, 20, None)
    assert result["projected_orders"] == 12
    assert result["projected_revenue"] is None
