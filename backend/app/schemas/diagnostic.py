"""Diagnostic contracts shared by SP-04A and SP-04B."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["seller", "assistant"]
    content: str = Field(min_length=1)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: str = Field(min_length=1)
    source: Literal[
        "math_analysis",
        "seller_context",
        "current_seller_message",
        "conversation_history",
    ]
    value: Any


class DiagnosticInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seller_context: dict[str, Any]
    math_analysis: dict[str, Any]
    current_seller_message: str = Field(min_length=1)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    known_data_limitations: list[str] = Field(default_factory=list)
    evidence_catalogue: list[EvidenceItem] = Field(default_factory=list)


class ContextObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation: str
    source: Literal["seller_reported", "verified", "system_observed"]
    evidence_references: list[str] = Field(default_factory=list)


class DiagnosticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: Literal[
        "lower_order_volume",
        "high_cancellation_rate",
        "inventory_availability",
        "low_product_visibility",
        "pricing_competitiveness",
        "unknown",
    ]

    title: str
    explanation: str
    classification: Literal["fact", "hypothesis"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_references: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class DiagnosticResult(BaseModel):
    """Structured diagnosis; recommendations are deliberately excluded."""
    model_config = ConfigDict(extra="forbid")
    status: Literal["complete", "needs_more_information", "unavailable"]
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    context_observations: list[ContextObservation] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    summary: str
