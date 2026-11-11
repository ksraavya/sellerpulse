"""Shared domain types and diagnostic contracts.

Issue identifiers are stable values for later diagnostic, recommendation,
and escalation milestones. This module does not diagnose sellers.
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    """Base model for seller-domain records."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


ReportingPeriod = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class IssueId(str, Enum):
    """Canonical business issue identifiers shared by future agents."""

    LOWER_ORDER_VOLUME = "lower_order_volume"
    HIGH_CANCELLATION_RATE = "high_cancellation_rate"
    INVENTORY_AVAILABILITY = "inventory_availability"
    LOW_PRODUCT_VISIBILITY = "low_product_visibility"
    PRICING_COMPETITIVENESS = "pricing_competitiveness"
    UNKNOWN = "unknown"


class IssueSeverity(str, Enum):
    """How serious a diagnostic finding is."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingStatus(str, Enum):
    """Whether a finding has been confirmed or is still a hypothesis."""

    CONFIRMED = "confirmed"
    HYPOTHETICAL = "hypothetical"


class Evidence(DomainModel):
    """One observation that supports a diagnostic finding."""

    metric: str = Field(min_length=1)
    value: str | int | float
    period: ReportingPeriod | None = None
    note: str | None = None


class DiagnosticFinding(DomainModel):
    """A structured finding a later diagnostic step can return.

    Confidence is a likelihood from 0 to 1. Status records whether the
    finding is confirmed or still hypothetical.
    """

    issue_id: IssueId
    severity: IssueSeverity
    description: str = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    status: FindingStatus
