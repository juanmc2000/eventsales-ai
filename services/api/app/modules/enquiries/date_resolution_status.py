"""Date Resolution Status Model (DATE-002).

Provides a reusable, deterministic representation of date certainty that
downstream services can consume without needing to understand the internals
of extraction or date resolution.

The model answers one question:
  "Can the system proceed with this date?"

Supported statuses:
  - resolved:                  Date is unambiguous and ready for availability lookup.
  - resolved_with_confirmation: System chose a most-likely interpretation but a
                                human-readable clarification question should be
                                presented to the guest before proceeding.
  - ambiguous:                 System cannot choose between interpretations;
                               availability lookup must not proceed.
  - unknown:                   No date information was extracted at all.

Fields:
  original_text:        The raw date phrase from the guest message.
  resolution_method:    How the date was resolved (e.g. "dd_mm_unambiguous",
                        "british_default", "relative_period_expansion", etc.)
  resolved_date:        The primary resolved date (ISO format string), or None.
  alternative_date:     Secondary interpretation when ambiguous (ISO format), or None.
  clarification_required: True when the guest should be asked to confirm before
                          availability lookups are made.
  clarification_reason:   Machine-readable reason code for why confirmation is needed.
  clarification_question: Human-readable question to present to the guest, or None.

This model integrates with:
  - NumericDateDisambiguationService (HOTFIX-001): wrap DisambiguationResult
    using DateResolutionStatus.from_disambiguation_result()
  - EnquiryDateResolutionService: call DateResolutionStatus.from_resolved_date()
    for cleanly resolved dates
  - ResponsePreparationService (RESP-001): consume status to decide response goal

No LLM calls are made.

Usage::

    # From a numeric disambiguation result:
    from app.modules.enquiries.numeric_date_disambiguation_service import (
        NumericDateDisambiguationService,
    )
    from app.modules.enquiries.date_resolution_status import DateResolutionStatus

    result = NumericDateDisambiguationService.disambiguate(7, 2, anchor_date)
    status = DateResolutionStatus.from_disambiguation_result(
        original_text="7/2", result=result
    )
    # status.status → "resolved_with_confirmation"

    # For a cleanly resolved date (no ambiguity):
    status = DateResolutionStatus.resolved("next Friday", "2026-06-07", "weekday_relative")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Import the constants from the disambiguation service to keep them consistent.
from app.modules.enquiries.numeric_date_disambiguation_service import (
    RESOLVED,
    RESOLVED_WITH_CONFIRMATION,
    UNRESOLVED_AMBIGUITY,
    DisambiguationResult,
)

# ── Status constants ───────────────────────────────────────────────────────────

STATUS_RESOLVED = "resolved"
STATUS_RESOLVED_WITH_CONFIRMATION = "resolved_with_confirmation"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_UNKNOWN = "unknown"

ALL_DATE_RESOLUTION_STATUSES = {
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_AMBIGUOUS,
    STATUS_UNKNOWN,
}

# ── Resolution method constants ────────────────────────────────────────────────

METHOD_DD_MM_UNAMBIGUOUS = "dd_mm_unambiguous"
METHOD_MM_DD_UNAMBIGUOUS = "mm_dd_unambiguous"
METHOD_BRITISH_DEFAULT = "british_default"
METHOD_AMERICAN_NEARER = "american_nearer_by_horizon_heuristic"
METHOD_NEXT_YEAR_ASSUMPTION = "next_year_assumption"
METHOD_BOTH_EQUALLY_PLAUSIBLE = "both_interpretations_equally_plausible"
METHOD_DATE_UNRESOLVABLE = "date_values_unresolvable"
METHOD_RELATIVE_PERIOD_EXPANSION = "relative_period_expansion"
METHOD_EXPLICIT_DATE = "explicit_date"
METHOD_WEEKDAY_RELATIVE = "weekday_relative"
METHOD_DATE_RANGE_EXPANSION = "date_range_expansion"
METHOD_NO_DATE_EXTRACTED = "no_date_extracted"
METHOD_UNKNOWN = "unknown"
# HOTFIX-008: near-horizon resolution (Rule 4)
METHOD_NEAR_HORIZON_BRITISH = "near_horizon_british"
METHOD_NEAR_HORIZON_AMERICAN = "near_horizon_american"

ALL_RESOLUTION_METHODS = {
    METHOD_DD_MM_UNAMBIGUOUS,
    METHOD_MM_DD_UNAMBIGUOUS,
    METHOD_BRITISH_DEFAULT,
    METHOD_AMERICAN_NEARER,
    METHOD_NEXT_YEAR_ASSUMPTION,
    METHOD_BOTH_EQUALLY_PLAUSIBLE,
    METHOD_DATE_UNRESOLVABLE,
    METHOD_RELATIVE_PERIOD_EXPANSION,
    METHOD_EXPLICIT_DATE,
    METHOD_WEEKDAY_RELATIVE,
    METHOD_DATE_RANGE_EXPANSION,
    METHOD_NO_DATE_EXTRACTED,
    METHOD_UNKNOWN,
    METHOD_NEAR_HORIZON_BRITISH,
    METHOD_NEAR_HORIZON_AMERICAN,
}


# ── Status model ───────────────────────────────────────────────────────────────


@dataclass
class DateResolutionStatus:
    """Deterministic representation of date certainty after resolution.

    Consumed by downstream services (response preparation, availability checks)
    without requiring knowledge of extraction or date-resolution internals.
    """

    status: str                          # One of ALL_DATE_RESOLUTION_STATUSES
    original_text: str | None            # Raw date phrase from guest message
    resolution_method: str               # How the date was resolved
    resolved_date: str | None            # Primary resolved date (ISO format)
    alternative_date: str | None         # Secondary interpretation (ISO), or None
    clarification_required: bool         # True if guest must confirm before proceeding
    clarification_reason: str | None     # Machine-readable reason code
    clarification_question: str | None   # Human-readable question for the guest
    candidate_dates: list[str] = field(default_factory=list)  # All resolved candidates

    @property
    def can_proceed_to_availability(self) -> bool:
        """True when availability checks may proceed without guest confirmation.

        Only STATUS_RESOLVED permits immediate availability lookup.
        All other statuses require either confirmation or cannot proceed at all.
        """
        return self.status == STATUS_RESOLVED

    @property
    def requires_guest_action(self) -> bool:
        """True when the guest must provide additional input before proceeding."""
        return self.clarification_required

    def to_dict(self) -> dict:
        """Serialise to a plain dict for storage or API serialisation."""
        return {
            "status": self.status,
            "original_text": self.original_text,
            "resolution_method": self.resolution_method,
            "resolved_date": self.resolved_date,
            "alternative_date": self.alternative_date,
            "clarification_required": self.clarification_required,
            "clarification_reason": self.clarification_reason,
            "clarification_question": self.clarification_question,
            "candidate_dates": self.candidate_dates,
            "can_proceed_to_availability": self.can_proceed_to_availability,
        }

    # ── Factory constructors ───────────────────────────────────────────────────

    @classmethod
    def from_disambiguation_result(
        cls,
        original_text: str | None,
        result: DisambiguationResult,
    ) -> "DateResolutionStatus":
        """Build a DateResolutionStatus from a NumericDateDisambiguationService result.

        This is the primary bridge between HOTFIX-001 (numeric date disambiguation)
        and DATE-002 (unified date resolution status).

        Args:
            original_text: The raw date phrase as extracted from the guest message.
            result: DisambiguationResult from NumericDateDisambiguationService.

        Returns:
            DateResolutionStatus with status mapped from DisambiguationResult.ambiguity_type.
        """
        # Map disambiguation ambiguity_type to DateResolutionStatus status
        if result.ambiguity_type == RESOLVED:
            status = STATUS_RESOLVED
        elif result.ambiguity_type == RESOLVED_WITH_CONFIRMATION:
            status = STATUS_RESOLVED_WITH_CONFIRMATION
        else:  # UNRESOLVED_AMBIGUITY or anything unexpected
            status = STATUS_AMBIGUOUS

        # Map clarification_reason to a resolution method
        resolution_method = cls._map_clarification_reason(
            result.clarification_reason, result.ambiguity_type
        )

        resolved_date = result.assumed_date.isoformat() if result.assumed_date else None
        alternative_date = result.alternative_date.isoformat() if result.alternative_date else None

        candidates = []
        if resolved_date:
            candidates.append(resolved_date)
        if alternative_date:
            candidates.append(alternative_date)

        return cls(
            status=status,
            original_text=original_text,
            resolution_method=resolution_method,
            resolved_date=resolved_date,
            alternative_date=alternative_date,
            clarification_required=result.clarification_required,
            clarification_reason=result.clarification_reason,
            clarification_question=result.clarification_question,
            candidate_dates=candidates,
        )

    @classmethod
    def resolved(
        cls,
        original_text: str | None,
        resolved_date: str,
        resolution_method: str = METHOD_UNKNOWN,
        candidate_dates: list[str] | None = None,
    ) -> "DateResolutionStatus":
        """Convenience constructor for an unambiguous, confirmed resolved date.

        Use when the backend has expanded a date without any ambiguity and no
        guest confirmation is required.
        """
        return cls(
            status=STATUS_RESOLVED,
            original_text=original_text,
            resolution_method=resolution_method,
            resolved_date=resolved_date,
            alternative_date=None,
            clarification_required=False,
            clarification_reason=None,
            clarification_question=None,
            candidate_dates=candidate_dates or [resolved_date],
        )

    @classmethod
    def unknown(cls, original_text: str | None = None) -> "DateResolutionStatus":
        """Convenience constructor when no date information was extracted."""
        return cls(
            status=STATUS_UNKNOWN,
            original_text=original_text,
            resolution_method=METHOD_NO_DATE_EXTRACTED,
            resolved_date=None,
            alternative_date=None,
            clarification_required=True,
            clarification_reason="no_date_extracted",
            clarification_question="Could you let us know when you would like to book?",
            candidate_dates=[],
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _map_clarification_reason(
        reason: str | None,
        ambiguity_type: str,
    ) -> str:
        """Map a disambiguation clarification_reason to a resolution_method string."""
        mapping = {
            # RESOLVED reasons
            "near_horizon_british": METHOD_NEAR_HORIZON_BRITISH,     # HOTFIX-008 Rule 4
            "near_horizon_american": METHOD_NEAR_HORIZON_AMERICAN,   # HOTFIX-008 Rule 4
            # RESOLVED_WITH_CONFIRMATION / UNRESOLVED_AMBIGUITY reasons
            "american_nearer_by_horizon_heuristic": METHOD_AMERICAN_NEARER,
            "next_year_assumption": METHOD_NEXT_YEAR_ASSUMPTION,
            "both_interpretations_equally_plausible": METHOD_BOTH_EQUALLY_PLAUSIBLE,
            "date_values_unresolvable": METHOD_DATE_UNRESOLVABLE,
            "british_date_invalid": METHOD_MM_DD_UNAMBIGUOUS,
            "american_date_invalid": METHOD_DD_MM_UNAMBIGUOUS,
            "british_default": METHOD_BRITISH_DEFAULT,
        }
        if reason in mapping:
            return mapping[reason]

        if ambiguity_type == RESOLVED:
            # Rule 1a or 1b: one value > 12, no reason code set
            return METHOD_DD_MM_UNAMBIGUOUS

        return METHOD_UNKNOWN
