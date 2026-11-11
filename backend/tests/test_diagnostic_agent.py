from app.agents.diagnostic_agent import DiagnosticAgent
from app.schemas.diagnostic import (
    ContextObservation,
    DiagnosticFinding,
    DiagnosticInput,
    DiagnosticResult,
    EvidenceItem,
)


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def generate(self, diagnostic_input):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def make_input():
    return DiagnosticInput(
        seller_context={"seller_id": "demo-seller"},
        math_analysis={"latest_cancellation_rate": 0.4234},
        current_seller_message="My cancellations have increased.",
        evidence_catalogue=[
            EvidenceItem(
                reference="math_analysis.latest_cancellation_rate",
                source="math_analysis",
                value=0.4234,
            ),
            EvidenceItem(
                reference="current_seller_message",
                source="current_seller_message",
                value="My cancellations have increased.",
            ),
        ],
    )


def test_agent_calls_provider_once_and_returns_grounded_result():
    expected = DiagnosticResult(
        status="complete",
        findings=[
            DiagnosticFinding(
                issue_id="high_cancellation_rate",
                title="Elevated cancellations",
                explanation="The latest cancellation rate is elevated.",
                classification="fact",
                confidence=0.95,
                evidence_references=[
                    "math_analysis.latest_cancellation_rate"
                ],
            )
        ],
        context_observations=[
            ContextObservation(
                observation="Seller reports increased cancellations.",
                source="seller_reported",
                evidence_references=["current_seller_message"],
            )
        ],
        summary="Cancellations appear to be an important issue.",
    )
    provider = FakeProvider(result=expected)

    result = DiagnosticAgent(provider).diagnose(make_input())

    assert provider.calls == 1
    assert result.status == "complete"
    assert result.findings[0].classification == "fact"
    assert result.findings[0].evidence_references == [
        "math_analysis.latest_cancellation_rate"
    ]


def test_invalid_evidence_reference_is_removed_and_fact_downgraded():
    expected = DiagnosticResult(
        status="complete",
        findings=[
            DiagnosticFinding(
                issue_id="low_product_visibility",
                title="Possible visibility issue",
                explanation="Visibility may be contributing.",
                classification="fact",
                confidence=0.9,
                evidence_references=["made_up.reference"],
            )
        ],
        summary="There may be a visibility issue.",
    )

    result = DiagnosticAgent(FakeProvider(result=expected)).diagnose(make_input())

    finding = result.findings[0]
    assert finding.evidence_references == []
    assert finding.classification == "hypothesis"
    assert finding.confidence <= 0.3
    assert finding.missing_information
    assert result.data_limitations


def test_unavailable_provider_returns_safe_unavailable_result():
    result = DiagnosticAgent(
        FakeProvider(error=RuntimeError("provider down"))
    ).diagnose(make_input())

    assert result.status == "unavailable"
    assert result.findings == []
    assert "couldn't complete" in result.summary.lower()


def test_ungrounded_context_observation_is_omitted():
    expected = DiagnosticResult(
        status="complete",
        context_observations=[
            ContextObservation(
                observation="Competitor is cheaper.",
                source="seller_reported",
                evidence_references=["unknown.reference"],
            )
        ],
        summary="No supported findings yet.",
    )

    result = DiagnosticAgent(FakeProvider(result=expected)).diagnose(make_input())

    assert result.context_observations == []
    assert any("omitted" in item for item in result.data_limitations)


def test_no_recommendations_field_in_diagnostic_contract():
    assert "recommendations" not in DiagnosticResult.model_fields
