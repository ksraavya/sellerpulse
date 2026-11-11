"""Deterministic what-if calculations. Results are hypothetical, not forecasts."""

from __future__ import annotations

from app.analytics.calculations import safe_percentage_change


def order_recovery_scenario(
    baseline_orders: int,
    recovery_percent: float,
    baseline_revenue_per_order: float | None,
) -> dict:
    """Model an order increase relative to baseline orders."""
    if baseline_orders < 0:
        raise ValueError("baseline_orders cannot be negative")
    if not 0 <= recovery_percent <= 500:
        raise ValueError("recovery_percent must be between 0 and 500")
    projected_orders = round(baseline_orders * (1 + recovery_percent / 100))
    projected_revenue = (
        projected_orders * baseline_revenue_per_order
        if baseline_revenue_per_order is not None else None
    )
    baseline_revenue = (
        baseline_orders * baseline_revenue_per_order
        if baseline_revenue_per_order is not None else None
    )
    return {
        "scenario_type": "order_recovery",
        "assumptions": {
            "recovery_percent": recovery_percent,
            "revenue_per_order_held_constant": baseline_revenue_per_order is not None,
        },
        "baseline_orders": baseline_orders,
        "projected_orders": projected_orders,
        "order_difference": projected_orders - baseline_orders,
        "baseline_revenue": baseline_revenue,
        "projected_revenue": projected_revenue,
        "revenue_difference": (
            projected_revenue - baseline_revenue
            if projected_revenue is not None and baseline_revenue is not None else None
        ),
        "revenue_change_percent": (
            safe_percentage_change(baseline_revenue, projected_revenue)
            if baseline_revenue is not None and projected_revenue is not None else None
        ),
        "is_hypothetical": True,
    }


def cancellation_reduction_scenario(
    completed_orders: int,
    cancelled_orders: int,
    reduction_percentage_points: float,
    average_revenue_per_order: float | None,
) -> dict:
    """Model a percentage-point reduction in cancellation rate.

    The model holds total order opportunities constant and converts the
    reduction in cancellations into additional completed orders.
    """
    if completed_orders < 0 or cancelled_orders < 0:
        raise ValueError("Order counts cannot be negative")
    if not 0 <= reduction_percentage_points <= 100:
        raise ValueError("reduction_percentage_points must be between 0 and 100")

    total = completed_orders + cancelled_orders
    if total == 0:
        raise ValueError("Cannot model cancellation reduction when total orders are zero")

    current_rate = cancelled_orders / total * 100
    target_rate = max(0.0, current_rate - reduction_percentage_points)
    projected_completed = round(total * (1 - target_rate / 100))
    additional_completed = max(0, projected_completed - completed_orders)

    revenue_impact = (
        additional_completed * average_revenue_per_order
        if average_revenue_per_order is not None else None
    )
    return {
        "scenario_type": "cancellation_reduction",
        "assumptions": {
            "reduction_percentage_points": reduction_percentage_points,
            "total_order_opportunities_held_constant": True,
            "average_revenue_per_order_held_constant": average_revenue_per_order is not None,
        },
        "current_cancellation_rate_percent": current_rate,
        "projected_cancellation_rate_percent": target_rate,
        "baseline_completed_orders": completed_orders,
        "projected_completed_orders": projected_completed,
        "additional_completed_orders": additional_completed,
        "estimated_additional_revenue": revenue_impact,
        "is_hypothetical": True,
    }


def revenue_recovery_scenario(
    baseline_revenue: float,
    target_revenue: float,
) -> dict:
    """Calculate the gap to a stated historical revenue target."""
    if baseline_revenue < 0 or target_revenue < 0:
        raise ValueError("Revenue values cannot be negative")
    difference = target_revenue - baseline_revenue
    return {
        "scenario_type": "revenue_recovery",
        "baseline_revenue": baseline_revenue,
        "target_revenue": target_revenue,
        "revenue_difference": difference,
        "required_change_percent": safe_percentage_change(baseline_revenue, target_revenue),
        "is_hypothetical": True,
    }
