"""LLM provider boundary for the SP-05 Recommendation Agent."""
from __future__ import annotations

import json
import logging
import os
from typing import Protocol

from app.schemas.recommendation import RecommendationPlan

logger = logging.getLogger(__name__)


class RecommendationProviderError(RuntimeError):
    """Raised when the recommendation provider cannot return a usable plan."""


class RecommendationLLMProvider(Protocol):
    def generate(self, payload: dict) -> RecommendationPlan:
        """Generate a structured recommendation plan."""


class OpenAIRecommendationProvider:
    """OpenAI Responses API provider using Pydantic Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise RecommendationProviderError(
                "OPENAI_API_KEY is not configured. Add it to backend/.env."
            )

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RecommendationProviderError(
                "The OpenAI Python SDK is not installed. Run pip install -r requirements.txt."
            ) from exc

        self.client = OpenAI(
            api_key=resolved_key,
            timeout=timeout_seconds,
            max_retries=1,
        )

    def generate(self, payload: dict) -> RecommendationPlan:
        from app.agents.recommendation_prompts import RECOMMENDATION_SYSTEM_PROMPT

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Create practical recommendations using only the "
                            "supplied seller context, metrics and diagnostic findings.\n\n"
                            "RECOMMENDATION INPUT:\n"
                            + json.dumps(payload, ensure_ascii=False, indent=2)
                        ),
                    },
                ],
                text_format=RecommendationPlan,
            )
        except Exception as exc:
            logger.exception("OpenAI recommendation request failed")
            raise RecommendationProviderError(
                "The recommendation model request failed."
            ) from exc

        parsed = response.output_parsed
        if parsed is None:
            raise RecommendationProviderError(
                "The model did not return a structured recommendation plan."
            )
        if isinstance(parsed, RecommendationPlan):
            return parsed
        try:
            return RecommendationPlan.model_validate(parsed)
        except Exception as exc:
            raise RecommendationProviderError(
                "The model returned an invalid recommendation plan."
            ) from exc
