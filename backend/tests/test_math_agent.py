"""Tests for deterministic seller analysis."""

import pytest
from fastapi.testclient import TestClient

from app.agents.math_agent import MathAgent
from app.analytics.calculations import (
    average_order_value,
    cancellation_rate,
    click_through_rate,
    safe_percentage_change,
)
from app.analytics.scenarios import (
    cancellation_reduction_scenario,
    order_recovery_scenario,
    revenue_recovery_scenario,
)
from app.main import app
from app.schemas.context import SellerContext
from app.schemas.math_results import ScenarioRequest
from tests.conftest import build_seller_document


def test_safe_percentage_change_and_zero_baseline():
    assert safe_percentage_change(100, 80) == -20
    assert safe_percentage_change(100, 120) == 20
    assert safe_percentage_change(0, 10) is None


def test_rates_and_averages_handle_zero_denominators():
    assert cancellation_rate(90, 10) == 10
    assert cancellation_rate(0, 0) is None
    assert average_order_value(1000, 4) == 250
    assert average_order_value(1000, 0) is None
    assert click_through_rate(100, 5) == 5
    assert click_through_rate(0, 5) is None
    assert click_through_rate(None, 5) is None


def test_scenarios_are_deterministic_and_validated():
    result = order_recovery_scenario(100, 10, 250)
    assert result["projected_orders"] == 110
    assert result["projected_revenue"] == 27500
    with pytest.raises(ValueError):
        order_recovery_scenario(100, -1, 250)

    cancellation = cancellation_reduction_scenario(80, 20, 5, 100)
    assert cancellation["current_cancellation_rate_percent"] == 20
    assert cancellation["projected_cancellation_rate_percent"] == 15
    assert cancellation["additional_completed_orders"] == 5

    recovery = revenue_recovery_scenario(80, 100)
    assert recovery["revenue_difference"] == 20


def test_math_agent_analyzes_seller_context():
    payload = build_seller_document()
    payload["sales_snapshots"] = [
        {
            "period": "2026-09", "revenue": 1000, "completed_orders": 8,
            "cancelled_orders": 2, "units_sold": 10, "product_views": 100,
            "product_clicks": 20,
        },
        {
            "period": "2026-10", "revenue": 800, "completed_orders": 6,
            "cancelled_orders": 4, "units_sold": 8, "product_views": 80,
            "product_clicks": 8,
        },
    ]
    payload["product_performance"] = [
        {
            "product_id": "p1", "period": "2026-09", "revenue": 1000,
            "units_sold": 10, "product_views": 100, "product_clicks": 20,
        },
        {
            "product_id": "p1", "period": "2026-10", "revenue": 800,
            "units_sold": 8, "product_views": 80, "product_clicks": 8,
        },
    ]
    context = SellerContext.model_validate(payload)
    result = MathAgent().analyze(context)

    assert result.reporting_period_start == "2026-09"
    assert result.reporting_period_end == "2026-10"
    assert result.seller_metrics.total_revenue == 1800
    assert result.seller_metrics.revenue_change.absolute_change == -200
    assert result.seller_metrics.revenue_change.percentage_change == -20
    assert result.period_metrics[-1].cancellation_rate_percent == 40
    assert result.period_metrics[-1].click_through_rate_percent == 10
    assert result.product_metrics[0].revenue_contribution_percent == pytest.approx(100)
    assert result.seller_metrics.average_listed_selling_price == pytest.approx(200)
    assert result.product_metrics[0].selling_price == pytest.approx(200)
    assert result.inventory_metrics[0].risk_status == "healthy"


def test_empty_history_returns_unavailable_metrics():
    payload = build_seller_document()
    payload["sales_snapshots"] = []
    payload["product_performance"] = []
    result = MathAgent().analyze(SellerContext.model_validate(payload))
    assert result.periods_analyzed == 0
    assert result.seller_metrics.average_order_value is None
    assert result.visibility_metrics.total_views is None
    assert result.data_limitations


def test_demo_seller_math_agent_smoke():
    # This integration smoke test uses the app's configured seller service.
    client = TestClient(app)
    response = client.get("/api/sellers/demo-seller/analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["seller_id"] == "demo-seller"
    assert body["periods_analyzed"] == 6
    assert body["seller_metrics"]["total_completed_orders"] == 846
    assert body["seller_metrics"]["average_listed_selling_price"] == pytest.approx(
        (899 + 649 + 499) / 3
    )
    assert body["product_metrics"][0]["selling_price"] == 899


def test_unknown_seller_analysis_returns_404():
    client = TestClient(app)
    response = client.get("/api/sellers/not-real/analysis")
    assert response.status_code == 404


def test_scenario_api():
    client = TestClient(app)
    response = client.post(
        "/api/sellers/demo-seller/analysis/scenarios",
        json={"scenario_type": "order_recovery", "recovery_percent": 10},
    )
    assert response.status_code == 200
    assert response.json()["scenario"]["projected_orders"] > 0
