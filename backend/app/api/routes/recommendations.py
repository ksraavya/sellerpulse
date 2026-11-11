"""Seller recommendation endpoint."""
from fastapi import APIRouter, HTTPException, status

from app.agents.math_agent import MathAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.api.routes.sellers import SellerServiceDep
from app.schemas.diagnostic import DiagnosticResult
from app.schemas.recommendation import RecommendationResult
from app.services.seller_service import SellerNotFoundError

router = APIRouter(prefix="/api/sellers", tags=["recommendations"])
_math_agent = MathAgent()
_recommendation_agent = RecommendationAgent(math_agent=_math_agent)


@router.post(
    "/{seller_id}/recommendations",
    response_model=RecommendationResult,
)
def recommend_for_seller(
    seller_id: str,
    diagnostic_result: DiagnosticResult,
    service: SellerServiceDep,
) -> RecommendationResult:
    """Generate recommendations using current seller data and a prior diagnosis."""
    try:
        context = service.get_seller_context(seller_id)
    except SellerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    analysis = _math_agent.analyze(context)
    return _recommendation_agent.recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=diagnostic_result,
    )
