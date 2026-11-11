"""Seller API tests."""

from fastapi.testclient import TestClient

from app.api.routes.sellers import get_seller_service
from app.main import app
from app.repositories.json_seller_repository import JsonSellerRepository
from app.services.seller_service import SellerService

client = TestClient(app)


def test_list_sellers_returns_profiles_only() -> None:
    response = client.get("/api/sellers")

    assert response.status_code == 200
    body = response.json()
    ids = [item["seller_id"] for item in body]
    assert ids == ["demo-seller", "stable-seller"]
    assert "sales_snapshots" not in body[0]
    assert "products" not in body[0]
    assert body[0]["product_count"] >= 3


def test_get_demo_seller_returns_context() -> None:
    response = client.get("/api/sellers/demo-seller")

    assert response.status_code == 200
    body = response.json()
    assert body["seller"]["seller_id"] == "demo-seller"
    assert len(body["products"]) >= 3
    assert body["inventory"]
    assert body["sales_snapshots"]
    assert body["product_performance"]


def test_get_stable_seller_returns_context() -> None:
    response = client.get("/api/sellers/stable-seller")

    assert response.status_code == 200
    body = response.json()
    assert body["seller"]["seller_id"] == "stable-seller"
    assert body["seller"]["seller_status"] == "active"
    assert len(body["products"]) >= 3


def test_unknown_seller_returns_404() -> None:
    response = client.get("/api/sellers/not-a-seller")

    assert response.status_code == 404
    assert "not-a-seller" in response.json()["detail"]


def test_unavailable_seller_data_returns_an_error(tmp_path) -> None:
    missing_dir = tmp_path / "missing-sellers"
    service = SellerService(JsonSellerRepository(missing_dir))
    app.dependency_overrides[get_seller_service] = lambda: service
    try:
        response = client.get("/api/sellers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "does not exist" in response.json()["detail"]
    assert str(missing_dir) in response.json()["detail"]


def test_health_endpoint_still_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
