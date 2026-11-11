"""Seller repository contract."""

from typing import Protocol

from app.schemas.context import SellerContext


class SellerDataError(Exception):
    """Raised when seller data is missing, unreadable, or invalid."""


class SellerRepository(Protocol):
    """Storage operations the seller service needs."""

    def get_by_id(self, seller_id: str) -> SellerContext | None:
        """Return one seller context, or None when the id is unknown."""

    def list_ids(self) -> list[str]:
        """Return known seller ids in a stable order."""
