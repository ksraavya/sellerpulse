"""Domain schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    DiagnosticFinding,
    Evidence,
    FindingStatus,
    IssueId,
    IssueSeverity,
)
from app.schemas.context import SellerContext
from app.schemas.inventory import Inventory
from app.schemas.product import Product
from app.schemas.sales import SalesSnapshot
from app.schemas.seller import Seller


def test_valid_seller_profile(seller_document: dict) -> None:
    context = SellerContext.model_validate(seller_document)

    assert context.seller.seller_id == "seller-1"
    assert context.seller.business_name == "Example Stores"
    assert context.products[0].selling_price == 200
    assert context.inventory[0].available_quantity == 5
    assert context.sales_snapshots[0].period == "2026-10"


def test_invalid_seller_identifier() -> None:
    with pytest.raises(ValidationError):
        Seller(
            seller_id=" ",
            business_name="Example Stores",
            owner_name="Asha Verma",
            category="Home",
            city="Indore",
            seller_status="active",
        )


def test_negative_selling_price() -> None:
    with pytest.raises(ValidationError):
        Product(
            product_id="p1",
            seller_id="seller-1",
            product_name="Desk Lamp",
            category="Lighting",
            selling_price=-1,
            is_active=True,
        )


def test_negative_inventory_quantity() -> None:
    with pytest.raises(ValidationError):
        Inventory(
            product_id="p1",
            available_quantity=-3,
            reorder_threshold=2,
        )


def test_invalid_reporting_period() -> None:
    with pytest.raises(ValidationError):
        SalesSnapshot(
            period="2026-13",
            revenue=1000,
            completed_orders=4,
            cancelled_orders=1,
            units_sold=5,
        )


def test_duplicate_product_ids(seller_document: dict) -> None:
    seller_document["products"].append(dict(seller_document["products"][0]))

    with pytest.raises(ValidationError, match="Duplicate product identifiers"):
        SellerContext.model_validate(seller_document)


def test_inventory_referencing_unknown_product(seller_document: dict) -> None:
    seller_document["inventory"][0]["product_id"] = "missing-product"

    with pytest.raises(ValidationError, match="unknown product 'missing-product'"):
        SellerContext.model_validate(seller_document)


def test_product_must_belong_to_seller(seller_document: dict) -> None:
    seller_document["products"][0]["seller_id"] = "other-seller"

    with pytest.raises(ValidationError, match="expected 'seller-1'"):
        SellerContext.model_validate(seller_document)


def test_product_performance_referencing_unknown_product(seller_document: dict) -> None:
    seller_document["product_performance"][0]["product_id"] = "missing-product"

    with pytest.raises(ValidationError, match="unknown product 'missing-product'"):
        SellerContext.model_validate(seller_document)


def test_issue_identifiers_are_stable() -> None:
    assert IssueId.LOWER_ORDER_VOLUME == "lower_order_volume"
    assert IssueId.HIGH_CANCELLATION_RATE == "high_cancellation_rate"
    assert IssueId.INVENTORY_AVAILABILITY == "inventory_availability"
    assert IssueId.LOW_PRODUCT_VISIBILITY == "low_product_visibility"
    assert IssueId.PRICING_COMPETITIVENESS == "pricing_competitiveness"
    assert IssueId.UNKNOWN == "unknown"


def test_diagnostic_finding_records_hypothesis_and_evidence() -> None:
    finding = DiagnosticFinding(
        issue_id=IssueId.INVENTORY_AVAILABILITY,
        severity=IssueSeverity.HIGH,
        description="A listed product has no available units.",
        evidence=[
            Evidence(metric="available_quantity", value=0, period="2026-10"),
        ],
        confidence=0.9,
        status=FindingStatus.HYPOTHETICAL,
    )

    assert finding.status is FindingStatus.HYPOTHETICAL
    assert finding.evidence[0].value == 0
