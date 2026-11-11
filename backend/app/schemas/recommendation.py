"""Contracts for SP-05 recommendation generation and scenario enrichment."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import DomainModel


IssueIdValue = Literal[
    "lower_order_volume",
    "high_cancellation_rate",
    "inventory_availability",
    "low_product_visibility",
    "pricing_competitiveness",
    "unknown",
]


class ScenarioProposal(DomainModel):
    """A deliberately hypothetical input for an existing Math Agent scenario."""

    scenario_type: Literal["order_recovery", "cancellation_reduction"]
    assumption_value: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_assumption_range(self) -> "ScenarioProposal":
        maximum = 500 if self.scenario_type == "order_recovery" else 100
        if self.assumption_value > maximum:
            raise ValueError(
                f"assumption_value must not exceed {maximum} for {self.scenario_type}"
            )
        return self


class RecommendationDraft(DomainModel):
    """LLM-authored recommendation before deterministic scenario calculation."""

    issue_id: IssueIdValue
    priority: Literal["high", "medium", "low"]
    title: str
    rationale: str
    actions: list[str]
    expected_outcome: str
    effort: Literal["low", "medium", "high"]
    timeframe: str
    evidence_references: list[str]
    scenario_proposal: ScenarioProposal | None = None


class RecommendationPlan(DomainModel):
    """Structured plan returned by the recommendation LLM."""

    recommendations: list[RecommendationDraft]
    summary: str


class Recommendation(RecommendationDraft):
    """Validated recommendation enriched with a deterministic scenario result."""

    scenario_calculation: dict | None = None


class RecommendationResult(DomainModel):
    """Public SP-05 result returned to the application."""

    status: Literal["complete", "needs_more_information", "unavailable"]
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=3)
    summary: str
    limitations: list[str] = Field(default_factory=list)
