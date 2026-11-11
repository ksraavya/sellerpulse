"""Prepare existing seller/math data and raw conversation text for diagnosis.

This is deterministic packaging, not natural-language extraction. The seller's
message is passed through unchanged; interpretation happens in SP-04B.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.diagnostic import (
    ConversationMessage,
    DiagnosticInput,
    EvidenceItem,
)


def _to_json_dict(value: BaseModel | dict[str, Any], field_name: str) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"{field_name} must be a Pydantic model or a dictionary")


def _flatten_evidence(
    value: Any,
    *,
    prefix: str,
    source: str,
) -> list[EvidenceItem]:
    """Create stable dotted-path references for supplied structured data."""
    items: list[EvidenceItem] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(
                _flatten_evidence(child, prefix=child_prefix, source=source)
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            items.extend(
                _flatten_evidence(child, prefix=child_prefix, source=source)
            )
    else:
        # Keep None values: they can explicitly show that a field is unavailable.
        items.append(
            EvidenceItem(reference=prefix, source=source, value=value)
        )

    return items


def build_diagnostic_input(
    *,
    seller_context: BaseModel | dict[str, Any],
    math_analysis: BaseModel | dict[str, Any],
    current_seller_message: str,
    conversation_history: list[ConversationMessage] | None = None,
    known_data_limitations: list[str] | None = None,
) -> DiagnosticInput:
    """Build a validated DiagnosticInput without interpreting seller language.

    No LLM is called here. `current_seller_message` is preserved exactly as
    supplied by the STT/text interface (apart from the non-empty validation).
    """
    seller_data = _to_json_dict(seller_context, "seller_context")
    math_data = _to_json_dict(math_analysis, "math_analysis")

    message = current_seller_message.strip()
    if not message:
        raise ValueError("current_seller_message cannot be empty")

    evidence = [
        *_flatten_evidence(
            seller_data, prefix="seller_context", source="seller_context"
        ),
        *_flatten_evidence(
            math_data, prefix="math_analysis", source="math_analysis"
        ),
        EvidenceItem(
            reference="current_seller_message",
            source="current_seller_message",
            value=message,
        ),
    ]

    history = conversation_history or []
    for index, entry in enumerate(history):
        evidence.append(
            EvidenceItem(
                reference=f"conversation_history[{index}]",
                source="conversation_history",
                value={"role": entry.role, "content": entry.content},
            )
        )

    return DiagnosticInput(
        seller_context=seller_data,
        math_analysis=math_data,
        current_seller_message=message,
        conversation_history=history,
        known_data_limitations=known_data_limitations or [],
        evidence_catalogue=evidence,
    )
