"""Contracts shared by the diagnostic input builder and the future LLM agent.

This module contains data structures only. It deliberately contains no diagnosis
rules, thresholds, note-extraction logic, or LLM/provider code.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessage(BaseModel):
    """A single message from the seller-facing conversation."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["seller", "assistant"]
    content: str = Field(min_length=1)


class EvidenceItem(BaseModel):
    """A traceable piece of information supplied to the Diagnostic Agent."""

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
    """Complete, prepared input for one diagnostic LLM request.

    Seller and math data are JSON snapshots of the existing SP-02/SP-03
    Pydantic models. This avoids duplicating or tightly coupling their schemas.
    """

    model_config = ConfigDict(extra="forbid")

    seller_context: dict[str, Any]
    math_analysis: dict[str, Any]
    current_seller_message: str = Field(min_length=1)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    known_data_limitations: list[str] = Field(default_factory=list)
    evidence_catalogue: list[EvidenceItem] = Field(default_factory=list)


class ContextObservation(BaseModel):
    """Relevant business context noticed in the seller's words or system data."""

    model_config = ConfigDict(extra="forbid")

    observation: str = Field(min_length=1)
    source: Literal["seller_reported", "verified", "system_observed"]
    evidence_references: list[str] = Field(default_factory=list)


class DiagnosticFinding(BaseModel):
    """One possible issue or explanation, grounded in supplied evidence."""

    model_config = ConfigDict(extra="forbid")

    issue_id: str | None = None
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    classification: Literal["fact", "hypothesis"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_references: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class DiagnosticResult(BaseModel):
    """Structured result expected from the future SP-04B LLM agent.

    Recommendations intentionally do not belong here; they are SP-05's job.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "needs_more_information"]
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    context_observations: list[ContextObservation] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)
