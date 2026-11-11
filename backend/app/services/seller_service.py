"""Seller lookup used by the API."""

from app.repositories.seller_repository import SellerDataError, SellerRepository
from app.schemas.context import SellerContext
from app.schemas.seller import SellerSummary


class SellerNotFoundError(LookupError):
    """Raised when a seller id is not in the repository."""

    def __init__(self, seller_id: str) -> None:
        self.seller_id = seller_id
        super().__init__(f"Seller '{seller_id}' was not found.")


class SellerService:
    """Business-facing access to validated seller contexts."""

    def __init__(self, repository: SellerRepository) -> None:
        self._repository = repository

    def get_seller_context(self, seller_id: str) -> SellerContext:
        """Return the full context for a seller."""
        context = self._repository.get_by_id(seller_id)
        if context is None:
            raise SellerNotFoundError(seller_id)
        return context

    def list_sellers(self) -> list[SellerSummary]:
        """Return profile summaries without sales history."""
        summaries: list[SellerSummary] = []
        for seller_id in self._repository.list_ids():
            context = self._repository.get_by_id(seller_id)
            if context is None:
                raise SellerDataError(
                    f"Seller '{seller_id}' was listed but could not be loaded."
                )
            seller = context.seller
            summaries.append(
                SellerSummary(
                    seller_id=seller.seller_id,
                    business_name=seller.business_name,
                    owner_name=seller.owner_name,
                    category=seller.category,
                    city=seller.city,
                    joined_at=seller.joined_at,
                    seller_status=seller.seller_status,
                    product_count=len(context.products),
                )
            )
        return summaries
