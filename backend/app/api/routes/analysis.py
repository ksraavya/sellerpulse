"""Seller analysis and what-if scenario endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.math_agent import MathAgent
from app.api.routes.sellers import SellerServiceDep
from app.schemas.math_results import (
    MathAnalysisResult,
    ScenarioRequest,
    ScenarioResult,
)
from app.services.seller_service import SellerNotFoundError

router = APIRouter(prefix="/api/sellers", tags=["analysis"])
_math_agent = MathAgent()


@router.get("/{seller_id}/analysis", response_model=MathAnalysisResult)
def analyze_seller(seller_id: str, service: SellerServiceDep) -> MathAnalysisResult:
    """Return deterministic metrics and trends for one seller."""
    try:
        context = service.get_seller_context(seller_id)
    except SellerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _math_agent.analyze(context)


@router.post("/{seller_id}/analysis/scenarios", response_model=ScenarioResult)
def run_seller_scenario(
    seller_id: str,
    request: ScenarioRequest,
    service: SellerServiceDep,
) -> ScenarioResult:
    """Run a deterministic what-if scenario for one seller."""
    try:
        context = service.get_seller_context(seller_id)
    except SellerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    try:
        return _math_agent.run_scenario(context, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
