"""Pure, deterministic metric calculations."""

from __future__ import annotations


def safe_percentage_change(previous: float | int, current: float | int) -> float | None:
    """Return relative percentage change, or None when the baseline is zero."""
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0


def cancellation_rate(completed_orders: int, cancelled_orders: int) -> float | None:
    """Cancellation rate as a percentage of completed + cancelled orders."""
    denominator = completed_orders + cancelled_orders
    if denominator == 0:
        return None
    return cancelled_orders / denominator * 100.0


def average_order_value(revenue: float, completed_orders: int) -> float | None:
    """Revenue per completed order."""
    if completed_orders == 0:
        return None
    return revenue / completed_orders


def average_revenue_per_unit(revenue: float, units_sold: int) -> float | None:
    if units_sold == 0:
        return None
    return revenue / units_sold


def click_through_rate(views: int | None, clicks: int | None) -> float | None:
    """Clicks as a percentage of views; missing inputs remain unavailable."""
    if views is None or clicks is None or views == 0:
        return None
    return clicks / views * 100.0


def percentage_of(part: float | int, whole: float | int) -> float | None:
    if whole == 0:
        return None
    return part / whole * 100.0
