"""Sales snapshot and product performance models.

Period totals needed by later math stay as raw counts and amounts.
Rates and averages are derived later so they cannot drift from the source figures.
"""

from pydantic import Field

from app.schemas.common import DomainModel, ReportingPeriod


class SalesSnapshot(DomainModel):
    """Seller performance for one reporting month."""

    period: ReportingPeriod
    revenue: float = Field(ge=0)
    completed_orders: int = Field(ge=0)
    cancelled_orders: int = Field(ge=0)
    units_sold: int = Field(ge=0)
    product_views: int | None = Field(default=None, ge=0)
    product_clicks: int | None = Field(default=None, ge=0)


class ProductPerformance(DomainModel):
    """Product performance for one reporting month."""

    product_id: str = Field(min_length=1)
    period: ReportingPeriod
    revenue: float = Field(ge=0)
    units_sold: int = Field(ge=0)
    product_views: int | None = Field(default=None, ge=0)
    product_clicks: int | None = Field(default=None, ge=0)
