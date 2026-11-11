"""Product models."""

from pydantic import Field

from app.schemas.common import DomainModel


class Product(DomainModel):
    """A product listed by one seller."""

    product_id: str = Field(min_length=1)
    seller_id: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    selling_price: float = Field(ge=0)
    original_price: float | None = Field(default=None, ge=0)
    is_active: bool
