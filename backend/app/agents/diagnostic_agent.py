"""Stateless, evidence-grounded LLM Diagnostic Agent."""
from __future__ import annotations

import logging

from app.agents.diagnostic_provider import (
    DiagnosticLLMProvider,
    DiagnosticProviderError,
    OpenAIResponsesProvider,
)
from app.schemas.diagnostic import (
    ContextObservation,
    DiagnosticInput,
    DiagnosticResult,
)

logger = logging.getLogger(__name__)


class DiagnosticAgent:
    """Runs one LLM diagnosis and validates its evidence references.

    The agent does not retrieve seller data, manage conversation history,
    calculate metrics, or create recommendations. Those responsibilities
    belong to the data layer, Math Agent, LangGraph and SP-05 respectively.
    """

    def __init__(self, provider: DiagnosticLLMProvider | None = None) -> None:
        self.provider = provider

    def diagnose(self, diagnostic_input: DiagnosticInput) -> DiagnosticResult:
        provider = self.provider
        if provider is None:
            try:
                provider = OpenAIResponsesProvider()
            except DiagnosticProviderError:
                logger.exception("Diagnostic provider could not be initialized")
                return self._unavailable_result()

        try:
            result = provider.generate(diagnostic_input)
        except Exception:
            logger.exception("Diagnostic generation failed")
            return self._unavailable_result()

        return self._validate_evidence_references(result, diagnostic_input)

    @staticmethod
    def _unavailable_result() -> DiagnosticResult:
        return DiagnosticResult(
            status="unavailable",
            findings=[],
            context_observations=[],
            follow_up_questions=[],
            data_limitations=[
                "A diagnostic result could not be generated. Please try again."
            ],
            summary=(
                "I couldn't complete the diagnosis just now. "
                "Your business data has not been changed."
            ),
        )

    @staticmethod
    def _validate_evidence_references(
        result: DiagnosticResult,
        diagnostic_input: DiagnosticInput,
    ) -> DiagnosticResult:
        evidence_by_reference = {
            item.reference: item for item in diagnostic_input.evidence_catalogue
        }
        valid_references = set(evidence_by_reference)
        limitations = list(result.data_limitations)

        cleaned_findings = []
        for finding in result.findings:
            valid_refs = [
                ref for ref in finding.evidence_references
                if ref in valid_references
            ]
            invalid_refs_present = len(valid_refs) != len(
                finding.evidence_references
            )

            classification = finding.classification
            confidence = finding.confidence
            missing_information = list(finding.missing_information)

            if invalid_refs_present:
                limitations.append(
                    f"An unsupported evidence reference was removed from "
                    f"the finding '{finding.title}'."
                )

            # A finding without traceable evidence must not be stated as fact.
            fact_sources = {
                evidence_by_reference[ref].source for ref in valid_refs
            }
            has_system_evidence = bool(
                fact_sources.intersection({"math_analysis", "seller_context"})
            )
            if not valid_refs or (
                classification == "fact" and not has_system_evidence
            ):
                classification = "hypothesis"
                confidence = min(confidence, 0.3)
                missing_information.append(
                    "System-verified supporting evidence was not available."
                )

            cleaned_findings.append(
                finding.model_copy(
                    update={
                        "evidence_references": valid_refs,
                        "classification": classification,
                        "confidence": confidence,
                        "missing_information": list(dict.fromkeys(missing_information)),
                    }
                )
            )

        cleaned_observations = []
        for observation in result.context_observations:
            valid_refs = [
                ref for ref in observation.evidence_references
                if ref in valid_references
            ]
            if not valid_refs:
                # Observations without a traceable source are not retained.
                limitations.append(
                    "An ungrounded context observation was omitted."
                )
                continue

            cleaned_observations.append(
                observation.model_copy(
                    update={"evidence_references": valid_refs}
                )
            )

        return result.model_copy(
            update={
                "findings": cleaned_findings,
                "context_observations": cleaned_observations,
                "data_limitations": list(dict.fromkeys(limitations)),
            }
        )
