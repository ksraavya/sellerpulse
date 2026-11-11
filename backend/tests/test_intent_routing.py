from app.conversations.intent import HybridIntentClassifier, IntentClassification
from app.conversations.graph import ConversationGraph


class FakeIntentProvider:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def classify(self, message, *, has_pending_questions):
        self.calls += 1
        return self.result


def test_explicit_human_request_has_highest_priority():
    result, source = HybridIntentClassifier().classify(
        "My sales are falling. I want to speak to a human."
    )
    assert result.intent == "human_escalation"
    assert source == "rule"


def test_scenario_request_does_not_become_diagnosis():
    result, source = HybridIntentClassifier().classify(
        "What if I recover 10% of my orders?"
    )
    assert result.intent == "scenario_request"
    assert source == "rule"


def test_direct_metric_question_is_routed_without_llm():
    provider = FakeIntentProvider(IntentClassification(intent="unknown", confidence=0.0))
    result, source = HybridIntentClassifier(provider).classify("What was my revenue last month?")
    assert result.intent == "direct_question"
    assert source == "rule"
    assert provider.calls == 0


def test_pending_question_short_answer_is_information():
    result, _ = HybridIntentClassifier().classify("Yes, it was out of stock.", has_pending_questions=True)
    assert result.intent == "provide_information"


def test_ambiguous_message_uses_llm_fallback():
    provider = FakeIntentProvider(IntentClassification(intent="recommendation_request", confidence=0.82, reason="Asks for next steps"))
    result, source = HybridIntentClassifier(provider).classify("Can you help me figure out my next move?")
    assert result.intent == "recommendation_request"
    assert source == "llm"
    assert provider.calls == 1


def test_low_confidence_llm_result_falls_back_to_unknown():
    provider = FakeIntentProvider(IntentClassification(intent="diagnosis_request", confidence=0.3))
    result, source = HybridIntentClassifier(provider).classify("Something feels off")
    assert result.intent == "unknown"
    assert source == "fallback"


def test_graph_routes_message_and_preserves_history(tmp_path):
    graph = ConversationGraph(tmp_path / "conversations.sqlite3")
    try:
        session = graph.create_session("session-1", "demo-seller")
        result = graph.send_message("session-1", "What was my revenue last month?")
        assert result["current_intent"] == "direct_question"
        assert result["next_action"] == "answer_from_context"
        assert [m["role"] for m in result["messages"]] == ["assistant", "seller", "assistant"]
    finally:
        graph.close()
