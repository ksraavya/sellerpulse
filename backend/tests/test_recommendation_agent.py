from pathlib import Path

import pytest

from app.agents.recommendation_agent import RecommendationAgent
from app.repositories.json_seller_repository import JsonSellerRepository
from app.schemas.context import SellerContext
from app.schemas.diagnostic import DiagnosticFinding, DiagnosticResult
from app.schemas.math_results import MathAnalysisResult
from app.agents.math_agent import MathAgent
from app.schemas.recommendation import RecommendationPlan


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "sellers"


class FakeProvider:
    def __init__(self, plan):
        self.plan = plan
        self.calls = 0

    def generate(self, payload):
        self.calls += 1
        return self.plan


def load_context(seller_id="demo-seller"):
    repository = JsonSellerRepository(DATA_DIR)
    context = repository.get_by_id(seller_id)
    assert context is not None
    return context


def make_diagnosis():
    return DiagnosticResult(
        status="complete",
        findings=[
            DiagnosticFinding(
                issue_id="inventory_availability",
                title="Stock shortages may constrain sales",
                explanation="Two important products have low or no stock.",
                classification="hypothesis",
                confidence=0.78,
                evidence_references=[
                    "math_analysis.inventory_metrics[0].available_quantity",
                    "math_analysis.inventory_metrics[1].available_quantity",
                ],
            ),
            DiagnosticFinding(
                issue_id="high_cancellation_rate",
                title="Cancellations have increased",
                explanation="Cancellation rate has worsened.",
                classification="fact",
                confidence=0.9,
                evidence_references=[
                    "math_analysis.period_metrics[5].cancellation_rate_percent"
                ],
            ),
        ],
        summary="Inventory availability and cancellations need attention.",
    )


def make_plan():
    return RecommendationPlan(
        recommendations=[
            {
                "issue_id": "inventory_availability",
                "priority": "high",
                "title": "Restore availability of the storage box and kettle",
                "rationale": "Both products have low available stock and meaningful sales contribution.",
                "actions": [
                    "Confirm supplier replenishment lead times.",
                    "Prioritise replenishment for the storage box.",
                    "Review the kettle reorder quantity against recent demand.",
                ],
                "expected_outcome": "Reduce the time these products remain unavailable.",
                "effort": "medium",
                "timeframe": "Within 3–7 days",
                "evidence_references": [
                    "math_analysis.inventory_metrics[0].available_quantity"
                ],
                "scenario_proposal": None,
            },
            {
                "issue_id": "high_cancellation_rate",
                "priority": "medium",
                "title": "Audit cancellation reasons before changing fulfilment",
                "rationale": "The cancellation rate is elevated, but the reasons are not available.",
                "actions": [
                    "Review the latest cancelled orders.",
                    "Group cancellation reasons by product and fulfilment stage.",
                ],
                "expected_outcome": "Identify the main operational source of cancellations.",
                "effort": "low",
                "timeframe": "Within 2 days",
                "evidence_references": [
                    "math_analysis.period_metrics[5].cancellation_rate_percent"
                ],
                "scenario_proposal": {
                    "scenario_type": "cancellation_reduction",
                    "assumption_value": 5,
                },
            },
        ],
        summary="Prioritise replenishment and investigate cancellation causes before making broader changes.",
    )


def test_recommendations_are_generated_and_scenario_is_calculated():
    context = load_context()
    math_agent = MathAgent()
    analysis = math_agent.analyze(context)
    provider = FakeProvider(make_plan())
    agent = RecommendationAgent(provider=provider, math_agent=math_agent)

    result = agent.recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "complete"
    assert len(result.recommendations) == 2
    assert result.recommendations[0].scenario_calculation is None
    scenario = result.recommendations[1].scenario_calculation
    assert scenario is not None
    assert scenario["scenario_type"] == "cancellation_reduction"
    assert scenario["is_hypothetical"] is True
    assert scenario["current_cancellation_rate_percent"] == pytest.approx(42.3423423423)
    assert scenario["projected_cancellation_rate_percent"] == pytest.approx(37.3423423423)
    assert scenario["baseline_completed_orders"] == 64
    assert scenario["projected_completed_orders"] == 70
    assert scenario["additional_completed_orders"] == 6
    assert scenario["estimated_additional_revenue"] == pytest.approx(5046.1875)
    assert scenario["assumptions"]["total_order_opportunities_held_constant"] is True
    assert provider.calls == 1


def test_recommendation_with_unmatched_issue_is_omitted():
    context = load_context()
    analysis = MathAgent().analyze(context)
    plan = make_plan()
    plan.recommendations[0].issue_id = "pricing_competitiveness"
    agent = RecommendationAgent(provider=FakeProvider(plan))

    result = agent.recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "complete"
    assert len(result.recommendations) == 1
    assert "was omitted" in result.limitations[0]


def test_recommendation_without_valid_evidence_is_omitted():
    context = load_context()
    analysis = MathAgent().analyze(context)
    plan = make_plan()
    plan.recommendations[0].evidence_references = ["made.up.reference"]
    result = RecommendationAgent(provider=FakeProvider(plan)).recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "complete"
    assert len(result.recommendations) == 1
    assert "no valid diagnostic evidence" in result.limitations[0]


def test_unavailable_diagnosis_skips_llm_call():
    context = load_context()
    analysis = MathAgent().analyze(context)
    provider = FakeProvider(make_plan())
    diagnosis = DiagnosticResult(
        status="unavailable",
        summary="Diagnosis unavailable.",
    )

    result = RecommendationAgent(provider=provider).recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=diagnosis,
    )

    assert result.status == "needs_more_information"
    assert provider.calls == 0


def test_provider_failure_returns_unavailable():
    class BrokenProvider:
        def generate(self, payload):
            raise RuntimeError("provider failed")

    context = load_context()
    analysis = MathAgent().analyze(context)
    result = RecommendationAgent(provider=BrokenProvider()).recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "unavailable"
    assert result.recommendations == []


def test_scenario_proposal_rejects_out_of_range_assumption():
    from app.schemas.recommendation import ScenarioProposal

    with pytest.raises(ValueError):
        ScenarioProposal(
            scenario_type="cancellation_reduction",
            assumption_value=101,
        )



def test_order_recovery_scenario_is_calculated_with_expected_values():
    context = load_context()
    math_agent = MathAgent()
    analysis = math_agent.analyze(context)
    plan = make_plan()
    from app.schemas.recommendation import ScenarioProposal

    plan.recommendations[1].scenario_proposal = ScenarioProposal(
        scenario_type="order_recovery",
        assumption_value=10,
    )

    result = RecommendationAgent(
        provider=FakeProvider(plan), math_agent=math_agent
    ).recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "complete"
    scenario = result.recommendations[1].scenario_calculation
    assert scenario is not None
    assert scenario["scenario_type"] == "order_recovery"
    assert scenario["baseline_orders"] == 846
    assert scenario["projected_orders"] == 931
    assert scenario["order_difference"] == 85
    assert scenario["baseline_revenue"] == pytest.approx(706606.0)
    assert scenario["projected_revenue"] == pytest.approx(777600.6926713948)
    assert scenario["revenue_difference"] == pytest.approx(70994.69267139479)
    assert scenario["assumptions"]["recovery_percent"] == 10
    assert scenario["is_hypothetical"] is True


def test_scenario_is_not_executed_when_recommendation_has_no_proposal():
    class CountingMathAgent(MathAgent):
        def __init__(self):
            self.scenario_calls = 0

        def run_scenario(self, context, request):
            self.scenario_calls += 1
            return super().run_scenario(context, request)

    context = load_context()
    math_agent = CountingMathAgent()
    analysis = math_agent.analyze(context)
    plan = make_plan()
    plan.recommendations[1].scenario_proposal = None

    result = RecommendationAgent(
        provider=FakeProvider(plan), math_agent=math_agent
    ).recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "complete"
    assert all(item.scenario_calculation is None for item in result.recommendations)
    assert math_agent.scenario_calls == 0


def test_scenario_calculation_failure_does_not_drop_recommendation():
    class FailingMathAgent(MathAgent):
        def run_scenario(self, context, request):
            raise ValueError("scenario inputs are insufficient")

    context = load_context()
    analysis = MathAgent().analyze(context)
    result = RecommendationAgent(
        provider=FakeProvider(make_plan()), math_agent=FailingMathAgent()
    ).recommend(
        seller_context=context,
        math_analysis=analysis,
        diagnostic_result=make_diagnosis(),
    )

    assert result.status == "complete"
    assert len(result.recommendations) == 2
    assert result.recommendations[1].scenario_calculation is None
    assert any("what-if calculation" in item for item in result.limitations)
