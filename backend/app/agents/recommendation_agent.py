"""SP-05: evidence-grounded recommendations with deterministic scenario enrichment."""
from __future__ import annotations

import logging

from app.agents.math_agent import MathAgent
from app.agents.recommendation_provider import (
    OpenAIRecommendationProvider,
    RecommendationLLMProvider,
    RecommendationProviderError,
)
from app.schemas.context import SellerContext
from app.schemas.diagnostic import DiagnosticResult
from app.schemas.math_results import MathAnalysisResult, ScenarioRequest
from app.schemas.recommendation import (
    Recommendation,
    RecommendationPlan,
    RecommendationResult,
)

logger = logging.getLogger(__name__)


class RecommendationAgent:
    """Generate practical recommendations and calculate optional what-if scenarios."""

    def __init__(
        self,
        provider: RecommendationLLMProvider | None = None,
        math_agent: MathAgent | None = None,
    ) -> None:
        self.provider = provider
        self.math_agent = math_agent or MathAgent()

    def recommend(
        self,
        *,
        seller_context: SellerContext,
        math_analysis: MathAnalysisResult,
        diagnostic_result: DiagnosticResult,
    ) -> RecommendationResult:
        if diagnostic_result.status == "unavailable":
            return self._needs_more_information(
                "Recommendations are unavailable because the diagnosis could not be completed.",
                ["Complete the diagnostic step before requesting recommendations."],
            )

        if not diagnostic_result.findings:
            return self._needs_more_information(
                "There are not enough supported diagnostic findings to recommend meaningful actions.",
                diagnostic_result.data_limitations,
            )

        provider = self.provider
        if provider is None:
            try:
                provider = OpenAIRecommendationProvider()
            except RecommendationProviderError:
                logger.exception("Recommendation provider could not be initialized")
                return self._unavailable_result()

        payload = {
            "seller_context": seller_context.model_dump(mode="json"),
            "math_analysis": math_analysis.model_dump(mode="json"),
            "diagnostic_result": diagnostic_result.model_dump(mode="json"),
        }

        try:
            plan = provider.generate(payload)
        except Exception:
            logger.exception("Recommendation generation failed")
            return self._unavailable_result()

        valid_issue_ids = {finding.issue_id for finding in diagnostic_result.findings}
        valid_evidence = {
            reference
            for finding in diagnostic_result.findings
            for reference in finding.evidence_references
        }
        limitations: list[str] = []
        recommendations: list[Recommendation] = []

        for draft in plan.recommendations[:3]:
            if (
                not draft.title.strip()
                or not draft.rationale.strip()
                or not draft.expected_outcome.strip()
                or not draft.timeframe.strip()
                or not draft.actions
                or not any(action.strip() for action in draft.actions)
            ):
                limitations.append(
                    "A recommendation with incomplete action details was omitted."
                )
                continue

            if draft.issue_id not in valid_issue_ids:
                limitations.append(
                    f"Recommendation '{draft.title}' was omitted because its issue "
                    "was not present in the diagnostic report."
                )
                continue

            evidence_refs = [
                ref for ref in draft.evidence_references if ref in valid_evidence
            ]
            if not evidence_refs:
                limitations.append(
                    f"Recommendation '{draft.title}' was omitted because it had "
                    "no valid diagnostic evidence references."
                )
                continue

            scenario_calculation = None
            if draft.scenario_proposal is not None:
                proposal = draft.scenario_proposal
                try:
                    if proposal.scenario_type == "order_recovery":
                        request = ScenarioRequest(
                            scenario_type="order_recovery",
                            recovery_percent=proposal.assumption_value,
                        )
                    else:
                        request = ScenarioRequest(
                            scenario_type="cancellation_reduction",
                            reduction_percentage_points=proposal.assumption_value,
                        )
                    scenario_result = self.math_agent.run_scenario(
                        seller_context, request
                    )
                    scenario_calculation = scenario_result.scenario
                except (ValueError, TypeError) as exc:
                    limitations.append(
                        f"A what-if calculation for '{draft.title}' could not be "
                        f"generated: {exc}"
                    )

            recommendation_data = draft.model_dump(
                exclude={"scenario_proposal"}
            )
            recommendation_data["actions"] = [
                action for action in draft.actions if action.strip()
            ][:4]
            recommendation_data["evidence_references"] = evidence_refs

            recommendations.append(
                Recommendation(
                    **recommendation_data,
                    scenario_calculation=scenario_calculation,
                )
            )

        if not recommendations:
            return self._needs_more_information(
                "No recommendation could be safely grounded in the diagnostic evidence.",
                limitations or ["The diagnostic report did not support a usable recommendation."],
            )

        return RecommendationResult(
            status="complete",
            recommendations=recommendations,
            summary=plan.summary,
            limitations=list(dict.fromkeys(limitations)),
        )

    @staticmethod
    def _unavailable_result() -> RecommendationResult:
        return RecommendationResult(
            status="unavailable",
            recommendations=[],
            summary="I couldn't prepare recommendations just now. Please try again.",
            limitations=["The recommendation model did not return a usable result."],
        )

    @staticmethod
    def _needs_more_information(
        summary: str, limitations: list[str]
    ) -> RecommendationResult:
        return RecommendationResult(
            status="needs_more_information",
            recommendations=[],
            summary=summary,
            limitations=limitations,
        )
