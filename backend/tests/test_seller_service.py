"""Seller service tests using an in-memory repository."""

import pytest

from app.schemas.context import SellerContext
from app.services.seller_service import SellerNotFoundError, SellerService
from tests.conftest import build_seller_document


class InMemorySellerRepository:
    def __init__(self, documents: list[dict]) -> None:
        contexts = [SellerContext.model_validate(document) for document in documents]
        self._contexts = {context.seller.seller_id: context for context in contexts}

    def get_by_id(self, seller_id: str) -> SellerContext | None:
        return self._contexts.get(seller_id)

    def list_ids(self) -> list[str]:
        return sorted(self._contexts)


def test_get_seller_context_returns_full_record() -> None:
    service = SellerService(InMemorySellerRepository([build_seller_document()]))

    context = service.get_seller_context("seller-1")

    assert context.seller.business_name == "Example Stores"
    assert len(context.products) == 1
    assert context.sales_snapshots[0].completed_orders == 4
    assert context.product_performance[0].product_id == "p1"


def test_unknown_seller_raises() -> None:
    service = SellerService(InMemorySellerRepository([build_seller_document()]))

    with pytest.raises(SellerNotFoundError, match="missing-seller"):
        service.get_seller_context("missing-seller")


def test_list_sellers_returns_summaries_without_history() -> None:
    other = build_seller_document()
    other["seller"]["seller_id"] = "seller-2"
    other["seller"]["business_name"] = "Second Store"
    other["products"][0]["seller_id"] = "seller-2"
    service = SellerService(InMemorySellerRepository([build_seller_document(), other]))

    summaries = service.list_sellers()

    assert [item.seller_id for item in summaries] == ["seller-1", "seller-2"]
    assert summaries[1].business_name == "Second Store"
    assert summaries[0].product_count == 1
    assert not hasattr(summaries[0], "sales_snapshots")
