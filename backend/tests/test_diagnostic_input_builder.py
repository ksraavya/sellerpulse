import pytest
from pydantic import BaseModel

from app.diagnostics.input_builder import build_diagnostic_input
from app.schemas.diagnostic import ConversationMessage, DiagnosticInput


class SampleSellerContext(BaseModel):
    seller_id: str
    seller_name: str
    monthly_orders: list[int]


class SampleMathAnalysis(BaseModel):
    completed_orders: int
    cancellation_rate: float
    unavailable_metric: float | None = None


def test_builds_input_from_existing_pydantic_models():
    seller = SampleSellerContext(
        seller_id="demo-seller",
        seller_name="MetroHome Living",
        monthly_orders=[210, 64],
    )
    analysis = SampleMathAnalysis(
        completed_orders=846,
        cancellation_rate=0.4234,
    )

    result = build_diagnostic_input(
        seller_context=seller,
        math_analysis=analysis,
        current_seller_message="My sales have dropped recently.",
    )

    assert isinstance(result, DiagnosticInput)
    assert result.seller_context["seller_id"] == "demo-seller"
    assert result.math_analysis["completed_orders"] == 846
    assert result.current_seller_message == "My sales have dropped recently."
    assert any(
        item.reference == "math_analysis.cancellation_rate"
        and item.value == 0.4234
        for item in result.evidence_catalogue
    )


def test_preserves_seller_message_and_includes_conversation_history():
    message = "I increased the kettle price last week."
    history = [
        ConversationMessage(role="seller", content="Orders are falling."),
        ConversationMessage(role="assistant", content="When did you notice it?"),
    ]

    result = build_diagnostic_input(
        seller_context={"seller_id": "demo-seller"},
        math_analysis={"completed_orders": 64},
        current_seller_message=message,
        conversation_history=history,
    )

    assert result.current_seller_message == message
    assert result.conversation_history == history
    assert any(
        item.reference == "conversation_history[0]"
        and item.value["content"] == "Orders are falling."
        for item in result.evidence_catalogue
    )


def test_keeps_unavailable_values_visible_in_evidence_catalogue():
    result = build_diagnostic_input(
        seller_context={"seller_id": "demo-seller"},
        math_analysis={"average_order_value": None},
        current_seller_message="Why are orders falling?",
    )

    assert any(
        item.reference == "math_analysis.average_order_value"
        and item.value is None
        for item in result.evidence_catalogue
    )


def test_rejects_blank_seller_message():
    with pytest.raises(ValueError, match="cannot be empty"):
        build_diagnostic_input(
            seller_context={"seller_id": "demo-seller"},
            math_analysis={},
            current_seller_message="   ",
        )


def test_rejects_unsupported_input_types():
    with pytest.raises(TypeError, match="seller_context"):
        build_diagnostic_input(
            seller_context="not seller data",
            math_analysis={},
            current_seller_message="Hello",
        )
