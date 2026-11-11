"""Deterministic Math Agent: computes metrics, never diagnoses or recommends."""

from __future__ import annotations

from datetime import datetime, timezone

from app.analytics.calculations import (
    average_order_value,
    average_revenue_per_unit,
    cancellation_rate,
    click_through_rate,
    percentage_of,
)
from app.analytics.scenarios import (
    cancellation_reduction_scenario,
    order_recovery_scenario,
    revenue_recovery_scenario,
)
from app.analytics.trends import period_change, sorted_by_period
from app.schemas.context import SellerContext
from app.schemas.math_results import (
    InventoryMetric,
    MathAnalysisResult,
    MetricChange,
    PeriodMetrics,
    ProductMetrics,
    ScenarioRequest,
    ScenarioResult,
    SellerMetrics,
    VisibilityMetrics,
)


class MathAgent:
    """Analyze one validated seller context using deterministic calculations."""

    def analyze(self, context: SellerContext) -> MathAnalysisResult:
        snapshots = sorted_by_period(context.sales_snapshots)
        products_by_id = {product.product_id: product for product in context.products}
        total_revenue = sum(row.revenue for row in snapshots)
        total_completed = sum(row.completed_orders for row in snapshots)
        total_cancelled = sum(row.cancelled_orders for row in snapshots)
        total_units = sum(row.units_sold for row in snapshots)

        period_results: list[PeriodMetrics] = []
        for index, row in enumerate(snapshots):
            cancellation = cancellation_rate(row.completed_orders, row.cancelled_orders)
            revenue_change = orders_change = None
            cancellation_change = None
            if index:
                previous = snapshots[index - 1]
                absolute, percent = period_change(previous.revenue, row.revenue)
                revenue_change = MetricChange(
                    absolute_change=absolute, percentage_change=percent
                )
                absolute, percent = period_change(
                    previous.completed_orders, row.completed_orders
                )
                orders_change = MetricChange(
                    absolute_change=absolute, percentage_change=percent
                )
                previous_rate = cancellation_rate(
                    previous.completed_orders, previous.cancelled_orders
                )
                if previous_rate is not None and cancellation is not None:
                    cancellation_change = cancellation - previous_rate

            period_results.append(
                PeriodMetrics(
                    period=row.period,
                    revenue=row.revenue,
                    completed_orders=row.completed_orders,
                    cancelled_orders=row.cancelled_orders,
                    cancellation_rate_percent=cancellation,
                    units_sold=row.units_sold,
                    product_views=row.product_views,
                    product_clicks=row.product_clicks,
                    click_through_rate_percent=click_through_rate(
                        row.product_views, row.product_clicks
                    ),
                    revenue_change=revenue_change,
                    completed_orders_change=orders_change,
                    cancellation_rate_change_percentage_points=cancellation_change,
                )
            )

        revenue_change = orders_change = None
        if len(snapshots) >= 2:
            absolute, percent = period_change(snapshots[0].revenue, snapshots[-1].revenue)
            revenue_change = MetricChange(absolute_change=absolute, percentage_change=percent)
            absolute, percent = period_change(
                snapshots[0].completed_orders, snapshots[-1].completed_orders
            )
            orders_change = MetricChange(absolute_change=absolute, percentage_change=percent)

        available_rates = [
            cancellation_rate(row.completed_orders, row.cancelled_orders)
            for row in snapshots
        ]
        available_rates = [rate for rate in available_rates if rate is not None]
        latest_rate = (
            cancellation_rate(snapshots[-1].completed_orders, snapshots[-1].cancelled_orders)
            if snapshots else None
        )

        active_selling_prices = [
            product.selling_price for product in context.products if product.is_active
            for product in context.products
            if product.is_active
        ]       

        average_listed_selling_price = (
            sum(active_selling_prices) / len(active_selling_prices)
            if active_selling_prices else None
        )

        seller_metrics = SellerMetrics(
            total_revenue=total_revenue,
            total_completed_orders=total_completed,
            total_cancelled_orders=total_cancelled,
            total_units_sold=total_units,
            average_revenue_per_period=(
                total_revenue / len(snapshots) if snapshots else None
            ),
            average_completed_orders_per_period=(
                total_completed / len(snapshots) if snapshots else None
            ),
            latest_cancellation_rate_percent=latest_rate,
            average_cancellation_rate_percent=(
                sum(available_rates) / len(available_rates) if available_rates else None
            ),
            average_order_value=average_order_value(total_revenue, total_completed),
            average_revenue_per_unit=average_revenue_per_unit(total_revenue, total_units),
            average_listed_selling_price=average_listed_selling_price,
            revenue_change=revenue_change,
            completed_orders_change=orders_change,
        )

        product_results = []
        for product_id, product in products_by_id.items():
            records = sorted_by_period(
                row for row in context.product_performance if row.product_id == product_id
            )
            product_revenue = sum(row.revenue for row in records)
            product_units = sum(row.units_sold for row in records)
            views_present = bool(records) and all(row.product_views is not None for row in records)
            clicks_present = bool(records) and all(row.product_clicks is not None for row in records)
            total_views = sum(row.product_views for row in records) if views_present else None
            total_clicks = sum(row.product_clicks for row in records) if clicks_present else None

            rev_change = units_change = None
            if len(records) >= 2:
                absolute, percent = period_change(records[0].revenue, records[-1].revenue)
                rev_change = MetricChange(absolute_change=absolute, percentage_change=percent)
                absolute, percent = period_change(records[0].units_sold, records[-1].units_sold)
                units_change = MetricChange(absolute_change=absolute, percentage_change=percent)

            product_results.append(
                ProductMetrics(
                    product_id=product_id,
                    product_name=product.product_name,
                    selling_price=product.selling_price,
                    total_revenue=product_revenue,
                    total_units_sold=product_units,
                    revenue_contribution_percent=percentage_of(product_revenue, total_revenue),
                    units_contribution_percent=percentage_of(product_units, total_units),
                    total_views=total_views,
                    total_clicks=total_clicks,
                    click_through_rate_percent=click_through_rate(total_views, total_clicks),
                    revenue_change=rev_change,
                    units_change=units_change,
                )
            )
        product_results.sort(
            key=lambda item: item.revenue_contribution_percent or 0, reverse=True
        )

        inventory_results = []
        for item in context.inventory:
            product = products_by_id[item.product_id]
            if item.available_quantity == 0:
                risk = "critical"
            elif item.available_quantity <= item.reorder_threshold:
                risk = "low"
            else:
                risk = "healthy"
            inventory_results.append(
                InventoryMetric(
                    product_id=item.product_id,
                    product_name=product.product_name,
                    available_quantity=item.available_quantity,
                    reorder_threshold=item.reorder_threshold,
                    stockout_days=item.stockout_days,
                    risk_status=risk,
                )
            )

        views = [row.product_views for row in snapshots]
        clicks = [row.product_clicks for row in snapshots]
        all_views_present = bool(snapshots) and all(value is not None for value in views)
        all_clicks_present = bool(snapshots) and all(value is not None for value in clicks)
        total_views = sum(views) if all_views_present else None
        total_clicks = sum(clicks) if all_clicks_present else None

        views_change = clicks_change = None
        if len(snapshots) >= 2 and all_views_present:
            absolute, percent = period_change(views[0], views[-1])
            views_change = MetricChange(absolute_change=absolute, percentage_change=percent)
        if len(snapshots) >= 2 and all_clicks_present:
            absolute, percent = period_change(clicks[0], clicks[-1])
            clicks_change = MetricChange(absolute_change=absolute, percentage_change=percent)

        limitations = []
        if not snapshots:
            limitations.append("No seller sales history is available.")
        if snapshots and not all_views_present:
            limitations.append("Some seller-level product view values are unavailable.")
        if snapshots and not all_clicks_present:
            limitations.append("Some seller-level product click values are unavailable.")
        if len(snapshots) < 2:
            limitations.append("At least two reporting periods are required for trend comparisons.")

        return MathAnalysisResult(
            seller_id=context.seller.seller_id,
            analysis_timestamp=datetime.now(timezone.utc),
            reporting_period_start=snapshots[0].period if snapshots else None,
            reporting_period_end=snapshots[-1].period if snapshots else None,
            periods_analyzed=len(snapshots),
            seller_metrics=seller_metrics,
            period_metrics=period_results,
            product_metrics=product_results,
            inventory_metrics=inventory_results,
            visibility_metrics=VisibilityMetrics(
                total_views=total_views,
                total_clicks=total_clicks,
                click_through_rate_percent=click_through_rate(total_views, total_clicks),
                views_change=views_change,
                clicks_change=clicks_change,
            ),
            data_limitations=limitations,
        )

    def run_scenario(
        self, context: SellerContext, request: ScenarioRequest
    ) -> ScenarioResult:
        analysis = self.analyze(context)
        metrics = analysis.seller_metrics
        latest = context.sales_snapshots
        latest = sorted_by_period(latest)
        latest_snapshot = latest[-1] if latest else None

        if request.scenario_type == "order_recovery":
            if request.recovery_percent is None:
                raise ValueError("recovery_percent is required for order_recovery")
            scenario = order_recovery_scenario(
                baseline_orders=metrics.total_completed_orders,
                recovery_percent=request.recovery_percent,
                baseline_revenue_per_order=metrics.average_order_value,
            )
        elif request.scenario_type == "cancellation_reduction":
            if request.reduction_percentage_points is None:
                raise ValueError(
                    "reduction_percentage_points is required for cancellation_reduction"
                )
            if latest_snapshot is None:
                raise ValueError("Sales history is required for cancellation scenarios")
            scenario = cancellation_reduction_scenario(
                completed_orders=latest_snapshot.completed_orders,
                cancelled_orders=latest_snapshot.cancelled_orders,
                reduction_percentage_points=request.reduction_percentage_points,
                average_revenue_per_order=(
                    latest_snapshot.revenue / latest_snapshot.completed_orders
                    if latest_snapshot.completed_orders else None
                ),
            )
        else:
            if request.target_revenue is None:
                raise ValueError("target_revenue is required for revenue_recovery")
            if latest_snapshot is None:
                raise ValueError("Sales history is required for revenue scenarios")
            scenario = revenue_recovery_scenario(
                baseline_revenue=latest_snapshot.revenue,
                target_revenue=request.target_revenue,
            )

        return ScenarioResult(seller_id=context.seller.seller_id, scenario=scenario)
