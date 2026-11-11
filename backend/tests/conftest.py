"""Shared fixtures for seller domain tests."""

import copy

import pytest


def build_seller_document() -> dict:
    """Return a minimal valid seller context payload."""
    return {
        "seller": {
            "seller_id": "seller-1",
            "business_name": "Example Stores",
            "owner_name": "Asha Verma",
            "category": "Home",
            "city": "Indore",
            "joined_at": "2024-01-15",
            "seller_status": "active",
        },
        "products": [
            {
                "product_id": "p1",
                "seller_id": "seller-1",
                "product_name": "Desk Lamp",
                "category": "Lighting",
                "selling_price": 200,
                "original_price": 250,
                "is_active": True,
            }
        ],
        "inventory": [
            {
                "product_id": "p1",
                "available_quantity": 5,
                "reorder_threshold": 2,
            }
        ],
        "sales_snapshots": [
            {
                "period": "2026-10",
                "revenue": 1000,
                "completed_orders": 4,
                "cancelled_orders": 1,
                "units_sold": 5,
            }
        ],
        "product_performance": [
            {
                "product_id": "p1",
                "period": "2026-10",
                "revenue": 1000,
                "units_sold": 5,
            }
        ],
    }


@pytest.fixture
def seller_document() -> dict:
    return copy.deepcopy(build_seller_document())
