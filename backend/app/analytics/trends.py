"""Chronological trend calculations for seller and product metrics."""

from __future__ import annotations

from typing import Iterable

from app.analytics.calculations import safe_percentage_change


def sorted_by_period(records: Iterable):
    """Return records ordered by their YYYY-MM reporting period."""
    return sorted(records, key=lambda record: record.period)


def period_change(previous: float | int, current: float | int) -> tuple[float, float | None]:
    """Return absolute and relative change from one period to the next."""
    return current - previous, safe_percentage_change(previous, current)


def endpoint_change(values: list[float | int]) -> tuple[float, float | None]:
    """Compare the first and last values in an already ordered series."""
    if len(values) < 2:
        return 0.0, None
    return period_change(values[0], values[-1])
