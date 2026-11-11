"""Typed response contracts for deterministic Math Agent results."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import DomainModel


class MetricChange(DomainModel):
    absolute_change: float
    percentage_change: float | None = None


class PeriodMetrics(DomainModel):
    period: str
    revenue: float
    completed_orders: int
    cancelled_orders: int
    cancellation_rate_percent: float | None = None
    units_sold: int
    product_views: int | None = None
    product_clicks: int | None = None
    click_through_rate_percent: float | None = None
    revenue_change: MetricChange | None = None
    completed_orders_change: MetricChange | None = None
    cancellation_rate_change_percentage_points: float | None = None


class SellerMetrics(DomainModel):
    total_revenue: float
    total_completed_orders: int
    total_cancelled_orders: int
    total_units_sold: int
    average_revenue_per_period: float | None = None
    average_completed_orders_per_period: float | None = None
    latest_cancellation_rate_percent: float | None = None
    average_cancellation_rate_percent: float | None = None
    average_order_value: float | None = None
    average_revenue_per_unit: float | None = None
    average_listed_selling_price: float | None = None
    revenue_change: MetricChange | None = None
    completed_orders_change: MetricChange | None = None


class ProductMetrics(DomainModel):
    product_id: str
    product_name: str
    selling_price: float
    total_revenue: float
    total_units_sold: int
    revenue_contribution_percent: float | None = None
    units_contribution_percent: float | None = None
    total_views: int | None = None
    total_clicks: int | None = None
    click_through_rate_percent: float | None = None
    revenue_change: MetricChange | None = None
    units_change: MetricChange | None = None


class InventoryMetric(DomainModel):
    product_id: str
    product_name: str
    available_quantity: int
    reorder_threshold: int
    stockout_days: int | None = None
    risk_status: Literal["critical", "low", "healthy"]


class VisibilityMetrics(DomainModel):
    total_views: int | None = None
    total_clicks: int | None = None
    click_through_rate_percent: float | None = None
    views_change: MetricChange | None = None
    clicks_change: MetricChange | None = None


class MathAnalysisResult(DomainModel):
    seller_id: str
    analysis_timestamp: datetime
    reporting_period_start: str | None = None
    reporting_period_end: str | None = None
    periods_analyzed: int
    seller_metrics: SellerMetrics
    period_metrics: list[PeriodMetrics] = Field(default_factory=list)
    product_metrics: list[ProductMetrics] = Field(default_factory=list)
    inventory_metrics: list[InventoryMetric] = Field(default_factory=list)
    visibility_metrics: VisibilityMetrics
    data_limitations: list[str] = Field(default_factory=list)


class ScenarioRequest(DomainModel):
    scenario_type: Literal[
        "order_recovery", "cancellation_reduction", "revenue_recovery"
    ]
    recovery_percent: float | None = Field(default=None, ge=0, le=500)
    reduction_percentage_points: float | None = Field(default=None, ge=0, le=100)
    target_revenue: float | None = Field(default=None, ge=0)


class ScenarioResult(DomainModel):
    seller_id: str
    scenario: dict
    note: str = "Hypothetical calculation based on stated assumptions; not a guaranteed outcome."
