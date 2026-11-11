"""Seller profile models."""

from datetime import date
from enum import Enum

from pydantic import Field

from app.schemas.common import DomainModel


class SellerStatus(str, Enum):
    """Whether the seller is currently trading on the marketplace."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class Seller(DomainModel):
    """A marketplace seller profile."""

    seller_id: str = Field(min_length=1)
    business_name: str = Field(min_length=1)
    owner_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    city: str = Field(min_length=1)
    joined_at: date | None = None
    seller_status: SellerStatus


class SellerSummary(DomainModel):
    """Profile fields returned when listing sellers."""

    seller_id: str
    business_name: str
    owner_name: str
    category: str
    city: str
    joined_at: date | None = None
    seller_status: SellerStatus
    product_count: int = Field(ge=0)
