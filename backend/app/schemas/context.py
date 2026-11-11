"""Aggregate seller context consumed by later analysis steps."""

from pydantic import model_validator

from app.schemas.common import DomainModel
from app.schemas.inventory import Inventory
from app.schemas.product import Product
from app.schemas.sales import ProductPerformance, SalesSnapshot
from app.schemas.seller import Seller


class SellerContext(DomainModel):
    """One seller's profile, catalogue, stock, and sales history."""

    seller: Seller
    products: list[Product]
    inventory: list[Inventory]
    sales_snapshots: list[SalesSnapshot]
    product_performance: list[ProductPerformance]

    @model_validator(mode="after")
    def validate_relationships(self) -> "SellerContext":
        seller_id = self.seller.seller_id
        product_ids = [product.product_id for product in self.products]
        known_ids = set(product_ids)
        if len(known_ids) != len(product_ids):
            duplicates = sorted(
                product_id for product_id in known_ids if product_ids.count(product_id) > 1
            )
            raise ValueError(
                f"Duplicate product identifiers: {', '.join(duplicates)}."
            )

        for product in self.products:
            if product.seller_id != seller_id:
                raise ValueError(
                    f"Product '{product.product_id}' belongs to seller "
                    f"'{product.seller_id}', expected '{seller_id}'."
                )

        for item in self.inventory:
            if item.product_id not in known_ids:
                raise ValueError(
                    f"Inventory references unknown product '{item.product_id}'."
                )

        for record in self.product_performance:
            if record.product_id not in known_ids:
                raise ValueError(
                    f"Product performance references unknown product '{record.product_id}'."
                )

        return self
