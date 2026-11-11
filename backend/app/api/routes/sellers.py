"""Seller HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_seller_data_dir
from app.repositories.json_seller_repository import JsonSellerRepository
from app.schemas.context import SellerContext
from app.schemas.seller import SellerSummary
from app.services.seller_service import SellerNotFoundError, SellerService

router = APIRouter(prefix="/api/sellers", tags=["sellers"])

_service: SellerService | None = None


def get_seller_service() -> SellerService:
    """Build the JSON-backed seller service once per process."""
    global _service
    if _service is None:
        _service = SellerService(JsonSellerRepository(get_seller_data_dir()))
    return _service


SellerServiceDep = Annotated[SellerService, Depends(get_seller_service)]


@router.get("", response_model=list[SellerSummary])
def list_sellers(service: SellerServiceDep) -> list[SellerSummary]:
    """List seller profiles without historical records."""
    return service.list_sellers()


@router.get("/{seller_id}", response_model=SellerContext)
def get_seller(seller_id: str, service: SellerServiceDep) -> SellerContext:
    """Return the validated context for one seller."""
    try:
        return service.get_seller_context(seller_id)
    except SellerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
