"""LLM provider boundary for the Diagnostic Agent."""
from __future__ import annotations

import json
import logging
import os
from typing import Protocol

from app.schemas.diagnostic import DiagnosticInput, DiagnosticResult

logger = logging.getLogger(__name__)


class DiagnosticProviderError(RuntimeError):
    """Raised when an LLM provider cannot return a usable diagnostic result."""


class DiagnosticLLMProvider(Protocol):
    def generate(self, diagnostic_input: DiagnosticInput) -> DiagnosticResult:
        """Generate one structured diagnosis from the supplied input."""


class OpenAIResponsesProvider:
    """OpenAI Responses API implementation using Pydantic Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise DiagnosticProviderError(
                "OPENAI_API_KEY is not configured. Add it to backend/.env."
            )

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout_seconds = timeout_seconds

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise DiagnosticProviderError(
                "The OpenAI Python SDK is not installed. Run pip install -r requirements.txt."
            ) from exc

        self.client = OpenAI(
            api_key=resolved_key,
            timeout=timeout_seconds,
            max_retries=1,
        )

    def generate(self, diagnostic_input: DiagnosticInput) -> DiagnosticResult:
        from app.agents.diagnostic_prompts import DIAGNOSTIC_SYSTEM_PROMPT

        payload = diagnostic_input.model_dump(mode="json")

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": DIAGNOSTIC_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            "Diagnose the seller's situation using only the "
                            "provided context and evidence catalogue.\\n\\n"
                            "DIAGNOSTIC INPUT:\\n"
                            + json.dumps(payload, ensure_ascii=False, indent=2)
                        ),
                    },
                ],
                text_format=DiagnosticResult,
            )
        except Exception as exc:
            logger.exception("OpenAI diagnostic request failed")
            raise DiagnosticProviderError(
                "The diagnostic model request failed."
            ) from exc

        parsed = response.output_parsed
        if parsed is None:
            # This includes refusals or responses that did not produce the
            # requested structured object. Do not attempt to invent a result.
            raise DiagnosticProviderError(
                "The model did not return a structured diagnostic result."
            )

        if not isinstance(parsed, DiagnosticResult):
            try:
                return DiagnosticResult.model_validate(parsed)
            except Exception as exc:
                raise DiagnosticProviderError(
                    "The model returned an invalid diagnostic result."
                ) from exc

        return parsed
