"""Inventory models."""

from pydantic import Field

from app.schemas.common import DomainModel


class Inventory(DomainModel):
    """Current stock position for one product."""

    product_id: str = Field(min_length=1)
    available_quantity: int = Field(ge=0)
    reorder_threshold: int = Field(ge=0)
    stockout_days: int | None = Field(default=None, ge=0)
