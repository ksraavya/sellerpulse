"""Central LangGraph state. Agents remain stateless; the graph owns session context."""
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class ConversationState(TypedDict, total=False):
    session_id: str
    seller_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    greeted: bool
    status: Literal["active", "escalated", "closed"]
    current_intent: str | None
    intent_confidence: float
    intent_source: str
    intent_reason: str
    next_action: str
    response: str | None
    # Populated by subsequent SP-06 milestones.
    seller_context: dict[str, Any] | None
    math_analysis: dict[str, Any] | None
    diagnostic_findings: list[dict[str, Any]]
    context_observations: list[dict[str, Any]]
    pending_questions: list[dict[str, Any]]
    answered_questions: list[dict[str, Any]]
    unresolved_issues: list[str]
    recommendations: list[dict[str, Any]]
    recommendation_round: int
    question_count: int
    escalation_status: str | None
    handoff_summary: dict[str, Any] | None
