"""SP-06 conversation graph: persistent sessions and hybrid intent routing."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.conversations.intent import HybridIntentClassifier, IntentProvider
from app.conversations.state import ConversationState

DEFAULT_GREETING = (
    "Hey! Welcome to SellerPulse. I'm your virtual Key Account Manager. "
    "How are things going with your business today? Is there something "
    "specific you'd like us to look into, or would you like a quick "
    "overview of your store's performance?"
)


class ConversationGraph:
    """Owns graph compilation, session checkpointing and intent dispatch."""

    def __init__(
        self,
        database_path: str | Path = "data/conversations.sqlite3",
        *,
        intent_provider: IntentProvider | None = None,
    ) -> None:
        path = Path(database_path).expanduser()
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._checkpointer = SqliteSaver(self._connection)
        self._checkpointer.setup()
        self._classifier = HybridIntentClassifier(intent_provider)

        builder = StateGraph(ConversationState)
        builder.add_node("greet", self._greet)
        builder.add_node("classify_intent", self._classify_intent)
        builder.add_node("human_escalation", self._human_escalation)
        builder.add_node("scenario_request", self._scenario_request)
        builder.add_node("provide_information", self._provide_information)
        builder.add_node("diagnosis_request", self._diagnosis_request)
        builder.add_node("recommendation_request", self._recommendation_request)
        builder.add_node("direct_question", self._direct_question)
        builder.add_node("greeting", self._greeting)
        builder.add_node("unknown", self._unknown)
        builder.add_edge(START, "greet")
        builder.add_edge("greet", END)
        self._graph = builder.compile(checkpointer=self._checkpointer)

        message_builder = StateGraph(ConversationState)
        message_builder.add_node("classify_intent", self._classify_intent)
        for node in (
            "human_escalation", "scenario_request", "provide_information",
            "diagnosis_request", "recommendation_request", "direct_question",
            "greeting", "unknown",
        ):
            message_builder.add_node(node, getattr(self, f"_{node}"))
        message_builder.add_edge(START, "classify_intent")
        message_builder.add_conditional_edges(
            "classify_intent", self._route_intent,
            {
                "human_escalation": "human_escalation",
                "scenario_request": "scenario_request",
                "provide_information": "provide_information",
                "diagnosis_request": "diagnosis_request",
                "recommendation_request": "recommendation_request",
                "direct_question": "direct_question",
                "greeting": "greeting",
                "unknown": "unknown",
            },
        )
        for node in (
            "human_escalation", "scenario_request", "provide_information",
            "diagnosis_request", "recommendation_request", "direct_question",
            "greeting", "unknown",
        ):
            message_builder.add_edge(node, END)
        self._message_graph = message_builder.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _greet(state: ConversationState) -> dict[str, Any]:
        if state.get("greeted"):
            return {}
        return {
            "messages": [AIMessage(content=DEFAULT_GREETING)],
            "greeted": True, "status": "active",
            "response": DEFAULT_GREETING,
        }

    def _classify_intent(self, state: ConversationState) -> dict[str, Any]:
        latest = next(
            (message for message in reversed(state.get("messages", []))
             if isinstance(message, HumanMessage)), None,
        )
        if latest is None:
            return {"current_intent": "unknown", "intent_confidence": 0.0, "intent_source": "fallback"}
        classification, source = self._classifier.classify(
            str(latest.content),
            has_pending_questions=bool(state.get("pending_questions")),
        )
        return {
            "current_intent": classification.intent,
            "intent_confidence": classification.confidence,
            "intent_source": source,
            "intent_reason": classification.reason,
        }

    @staticmethod
    def _route_intent(state: ConversationState) -> str:
        intent = state.get("current_intent", "unknown")
        return intent if intent in {
            "human_escalation", "scenario_request", "provide_information",
            "diagnosis_request", "recommendation_request", "direct_question",
            "greeting",
        } else "unknown"

    @staticmethod
    def _response(state: ConversationState, intent: str, response: str, next_action: str) -> dict[str, Any]:
        return {
            "current_intent": intent, "response": response, "next_action": next_action,
            "messages": [AIMessage(content=response)],
        }

    def _human_escalation(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "human_escalation",
            "I understand you'd like to speak with a human Key Account Manager. I'll prepare that handoff for you.",
            "prepare_handoff")

    def _scenario_request(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "scenario_request",
            "Absolutely. Let's explore that what-if scenario using your store's numbers.",
            "run_scenario")

    def _provide_information(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "provide_information",
            "Thanks, that's helpful context. I'll use that information in the investigation.",
            "update_context")

    def _diagnosis_request(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "diagnosis_request",
            "Let's investigate that. I'll look at the relevant performance signals and narrow down the likely causes.",
            "run_diagnosis")

    def _recommendation_request(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "recommendation_request",
            "Let's focus on practical actions. I'll use the findings we already have before suggesting anything new.",
            "run_recommendations")

    def _direct_question(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "direct_question",
            "Sure — I'll use your store's performance data to answer that.",
            "answer_from_context")

    def _greeting(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "greeting",
            "Hey! Good to hear from you. What would you like to look into today?",
            "continue_conversation")

    def _unknown(self, state: ConversationState) -> dict[str, Any]:
        return self._response(state, "unknown",
            "I can help with store performance, sales issues, recommendations or what-if scenarios. What would you like to focus on?",
            "clarify_intent")

    def create_session(self, session_id: str, seller_id: str) -> dict[str, Any]:
        config = {"configurable": {"thread_id": session_id}}
        result = self._graph.invoke({
            "session_id": session_id, "seller_id": seller_id, "messages": [],
            "greeted": False, "status": "active", "current_intent": "greeting",
            "diagnostic_findings": [], "context_observations": [],
            "pending_questions": [], "answered_questions": [],
            "unresolved_issues": [], "recommendations": [],
            "recommendation_round": 0, "question_count": 0,
        }, config)
        return self._snapshot(result)

    def send_message(self, session_id: str, content: str) -> dict[str, Any] | None:
        config = {"configurable": {"thread_id": session_id}}
        current = self._graph.get_state(config)
        if not current.values:
            return None
        result = self._message_graph.invoke({"messages": [HumanMessage(content=content)]}, config)
        return self._snapshot(result)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        snapshot = self._graph.get_state({"configurable": {"thread_id": session_id}})
        if not snapshot.values:
            return None
        return self._snapshot(snapshot.values)

    @staticmethod
    def _snapshot(state: dict[str, Any]) -> dict[str, Any]:
        messages = []
        for message in state.get("messages", []):
            role = "seller" if isinstance(message, HumanMessage) else "assistant"
            messages.append({"role": role, "content": message.content})
        return {
            "session_id": state.get("session_id"), "seller_id": state.get("seller_id"),
            "status": state.get("status", "active"), "messages": messages,
            "response": state.get("response"), "current_intent": state.get("current_intent"),
            "intent_confidence": state.get("intent_confidence"),
            "intent_source": state.get("intent_source"),
            "intent_reason": state.get("intent_reason"),
            "next_action": state.get("next_action"),
        }

    def close(self) -> None:
        self._connection.close()


_graph: ConversationGraph | None = None

def get_conversation_graph() -> ConversationGraph:
    global _graph
    if _graph is None:
        database_path = os.getenv("CONVERSATION_DB_PATH", "data/conversations.sqlite3")
        _graph = ConversationGraph(database_path)
    return _graph
