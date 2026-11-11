"""JSON seller repository tests."""

import json

import pytest

from app.core.config import get_seller_data_dir
from app.repositories.json_seller_repository import JsonSellerRepository
from app.repositories.seller_repository import SellerDataError
from tests.conftest import build_seller_document


def test_loads_demo_and_stable_sellers() -> None:
    repository = JsonSellerRepository(get_seller_data_dir())

    demo = repository.get_by_id("demo-seller")
    stable = repository.get_by_id("stable-seller")

    assert demo is not None
    assert stable is not None
    assert demo.seller.business_name
    assert len(demo.products) >= 3
    assert len(stable.products) >= 3
    _assert_history_is_consistent(demo)
    _assert_history_is_consistent(stable)

    demo_orders = [row.completed_orders for row in _sorted_snapshots(demo)]
    demo_cancellations = [row.cancelled_orders for row in _sorted_snapshots(demo)]
    assert demo_orders[-1] < demo_orders[0]
    assert demo_cancellations[-1] > demo_cancellations[0]
    assert any(
        item.available_quantity <= item.reorder_threshold for item in demo.inventory
    )

    stable_orders = [row.completed_orders for row in _sorted_snapshots(stable)]
    assert max(stable_orders) - min(stable_orders) <= 30
    assert all(row.cancelled_orders <= 20 for row in stable.sales_snapshots)
    assert all(
        item.available_quantity > item.reorder_threshold for item in stable.inventory
    )


def test_unknown_seller_returns_none() -> None:
    repository = JsonSellerRepository(get_seller_data_dir())

    assert repository.get_by_id("missing-seller") is None


def test_list_ids_returns_available_sellers() -> None:
    repository = JsonSellerRepository(get_seller_data_dir())

    assert repository.list_ids() == ["demo-seller", "stable-seller"]


def test_missing_data_directory_raises(tmp_path) -> None:
    repository = JsonSellerRepository(tmp_path / "missing-sellers")

    with pytest.raises(SellerDataError, match="does not exist"):
        repository.get_by_id("demo-seller")


def test_malformed_json_raises(tmp_path) -> None:
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    repository = JsonSellerRepository(tmp_path)

    with pytest.raises(SellerDataError, match="Malformed JSON in broken.json"):
        repository.list_ids()


def test_invalid_record_is_not_ignored(tmp_path) -> None:
    valid = build_seller_document()
    invalid = build_seller_document()
    invalid["seller"]["seller_id"] = "broken-seller"
    invalid["products"][0]["selling_price"] = -10
    (tmp_path / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
    (tmp_path / "broken-seller.json").write_text(json.dumps(invalid), encoding="utf-8")
    repository = JsonSellerRepository(tmp_path)

    with pytest.raises(SellerDataError, match="Invalid seller record in broken-seller.json"):
        repository.get_by_id("seller-1")


def _sorted_snapshots(context):
    return sorted(context.sales_snapshots, key=lambda row: row.period)


def _assert_history_is_consistent(context) -> None:
    product_ids = {product.product_id for product in context.products}
    assert {item.product_id for item in context.inventory} <= product_ids
    assert {row.product_id for row in context.product_performance} <= product_ids

    for snapshot in context.sales_snapshots:
        rows = [
            row for row in context.product_performance if row.period == snapshot.period
        ]
        assert sum(row.units_sold for row in rows) == snapshot.units_sold
        assert sum(row.revenue for row in rows) == snapshot.revenue
        if snapshot.product_views is not None:
            assert sum(row.product_views or 0 for row in rows) == snapshot.product_views
        if snapshot.product_clicks is not None:
            assert sum(row.product_clicks or 0 for row in rows) == snapshot.product_clicks
