"""Hybrid intent classification for seller conversation turns."""
from __future__ import annotations

import logging
import os
import re
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

IntentName = Literal[
    "human_escalation",
    "scenario_request",
    "provide_information",
    "diagnosis_request",
    "recommendation_request",
    "direct_question",
    "greeting",
    "unknown",
]


class IntentClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: IntentName
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="")


class IntentProvider(Protocol):
    def classify(self, message: str, *, has_pending_questions: bool) -> IntentClassification: ...


class OpenAIIntentProvider:
    """Optional structured-output fallback for ambiguous natural-language turns."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, timeout=20.0, max_retries=1)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def classify(self, message: str, *, has_pending_questions: bool) -> IntentClassification:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Classify the seller's latest message into exactly one intent. "
                        "human_escalation: explicitly asks for a human/person/account manager. "
                        "scenario_request: asks a hypothetical what-if calculation. "
                        "provide_information: answers a previously asked follow-up question. "
                        "diagnosis_request: asks why a business metric/problem is happening or asks to investigate. "
                        "recommendation_request: asks what action to take. "
                        "direct_question: asks for a factual store metric or overview. "
                        "greeting: greeting or pleasantry. unknown: cannot confidently classify. "
                        "Do not treat a question as a diagnosis request merely because it mentions sales. "
                        "Prefer unknown over guessing. Return confidence conservatively."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Pending follow-up questions exist: {has_pending_questions}.\n"
                        f"Latest seller message: {message}"
                    ),
                },
            ],
            text_format=IntentClassification,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("Intent model returned no structured classification")
        return parsed if isinstance(parsed, IntentClassification) else IntentClassification.model_validate(parsed)


class HybridIntentClassifier:
    """Resolve high-certainty intents deterministically; use an LLM only as fallback."""

    def __init__(self, provider: IntentProvider | None = None) -> None:
        self.provider = provider

    def classify(
        self, message: str, *, has_pending_questions: bool = False
    ) -> tuple[IntentClassification, str]:
        text = " ".join(message.lower().strip().split())

        # Explicit requests for a human always win over every other route.
        if re.search(r"\b(speak to|talk to|connect me to|transfer me to|human|real person|account manager|representative|agent)\b", text):
            return IntentClassification(intent="human_escalation", confidence=1.0, reason="Explicit human handoff request."), "rule"

        if re.search(r"\b(what if|suppose|simulate|simulation|scenario|if i (recover|increase|reduce|decrease)|project the impact)\b", text):
            return IntentClassification(intent="scenario_request", confidence=0.96, reason="Hypothetical or scenario calculation requested."), "rule"

        # If the graph is waiting for an answer, short replies are treated as information.
        if has_pending_questions and (
            re.match(r"^(yes|no|yeah|yep|nope|sure|not really|i think so|maybe)\b", text)
            or re.search(r"\b(because|last week|yesterday|this week|out of stock)\b", text)
        ):
            return IntentClassification(intent="provide_information", confidence=0.88, reason="Seller appears to be answering a pending follow-up."), "rule"

        if re.fullmatch(r"(hi|hello|hey|good morning|good afternoon|good evening|thanks|thank you)[!. ]*", text):
            return IntentClassification(intent="greeting", confidence=0.99, reason="Greeting or pleasantry."), "rule"

        if re.search(r"\b(why|what caused|reason for|investigate|look into|diagnos)\b", text) or re.search(
            r"\b(sales|orders|revenue|visibility|traffic|cancellations|stock)\b.{0,35}\b(fall|fell|drop|dropped|declin|decreas|increas|high|low|problem|issue)\b", text
        ):
            return IntentClassification(intent="diagnosis_request", confidence=0.91, reason="Seller is asking to investigate a business issue."), "rule"

        if re.search(r"\b(recommend|recommendation|suggest|what should i do|next steps|how can i improve|action should)\b", text):
            return IntentClassification(intent="recommendation_request", confidence=0.9, reason="Seller is asking for practical actions."), "rule"

        if re.search(r"\b(what was|how much|how many|show me|overview|performance|revenue|orders|sales|gmv|aov|cancellation rate)\b", text) and ("?" in text or re.search(r"\b(what|how|show|give|tell)\b", text)):
            return IntentClassification(intent="direct_question", confidence=0.86, reason="Seller is requesting a factual metric or overview."), "rule"

        if self.provider is None:
            try:
                self.provider = OpenAIIntentProvider()
            except Exception:
                self.provider = None

        if self.provider is not None:
            try:
                result = self.provider.classify(message, has_pending_questions=has_pending_questions)
                if result.confidence >= 0.55:
                    return result, "llm"
            except Exception:
                logger.exception("LLM intent classification failed; using safe fallback")

        return IntentClassification(intent="unknown", confidence=0.0, reason="No high-confidence route was available."), "fallback"
