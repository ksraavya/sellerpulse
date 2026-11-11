"""Public conversation/session contracts for SP-06."""
from __future__ import annotations

from typing import Literal
from pydantic import Field
from app.schemas.common import DomainModel


class CreateConversationRequest(DomainModel):
    seller_id: str = Field(min_length=1, max_length=128)


class SendMessageRequest(DomainModel):
    content: str = Field(min_length=1, max_length=8000)


class ConversationMessageView(DomainModel):
    role: Literal["seller", "assistant"]
    content: str


class ConversationResponse(DomainModel):
    session_id: str
    seller_id: str
    status: Literal["active", "escalated", "closed"] = "active"
    messages: list[ConversationMessageView] = Field(default_factory=list)
    response: str | None = None
    current_intent: str | None = None
    intent_confidence: float | None = None
    intent_source: str | None = None
    intent_reason: str | None = None
    next_action: str | None = None
