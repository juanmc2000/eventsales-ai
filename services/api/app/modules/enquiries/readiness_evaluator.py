"""Enquiry Readiness Evaluator (ENQ-004).

Deterministic assessment layer that evaluates whether an enquiry has
sufficient extracted context to proceed to availability checking.

The evaluator answers the core POC question:
  "Can the system proceed with this enquiry?"

It does NOT:
- Make pricing decisions.
- Check room availability.
- Generate customer-facing copy.
- Call any LLM or AI provider.

All decisions are deterministic, testable, and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Readiness status constants ────────────────────────────────────────────────

STATUS_READY_FOR_AVAILABILITY = "READY_FOR_AVAILABILITY"
STATUS_NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
STATUS_WEBFORM_REQUIRED = "WEBFORM_REQUIRED"
STATUS_INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"

ALL_READINESS_STATUSES = {
    STATUS_READY_FOR_AVAILABILITY,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_WEBFORM_REQUIRED,
    STATUS_INSUFFICIENT_INFORMATION,
}


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class ReadinessEvaluation:
    """Result of a readiness evaluation.

    Fields mirror the evaluation criteria from the issue and are stored
    verbatim in normalized_json so downstream services and diagnostics
    can inspect the reasoning.
    """

    status: str                             # One of ALL_READINESS_STATUSES
    date_understood: bool
    guest_count_present: bool
    occasion_understood: bool
    meal_period_present: bool
    audience_identified: bool
    date_clarification_required: bool
    availability_check_possible: bool
    missing_for_availability: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialise to a plain dict for storage in normalized_json."""
        return {
            "status": self.status,
            "date_understood": self.date_understood,
            "guest_count_present": self.guest_count_present,
            "occasion_understood": self.occasion_understood,
            "meal_period_present": self.meal_period_present,
            "audience_identified": self.audience_identified,
            "date_clarification_required": self.date_clarification_required,
            "availability_check_possible": self.availability_check_possible,
            "missing_for_availability": self.missing_for_availability,
            "notes": self.notes,
        }


# ── Evaluator ─────────────────────────────────────────────────────────────────


class EnquiryReadinessEvaluator:
    """Evaluate whether an enquiry extraction has sufficient context to proceed.

    Usage::

        evaluator = EnquiryReadinessEvaluator()
        result = evaluator.evaluate(parsed_extraction)
        # result.status → "READY_FOR_AVAILABILITY"
    """

    def evaluate(self, parsed_extraction: dict | None) -> ReadinessEvaluation:
        """Evaluate the parsed extraction and return a ReadinessEvaluation.

        Always returns a ReadinessEvaluation — never raises.
        When parsed_extraction is None or empty, returns INSUFFICIENT_INFORMATION.

        Args:
            parsed_extraction: The validated extraction dict from the LLM
                (i.e. the ``parsed`` field on ExtractionResult), or None when
                extraction failed.

        Returns:
            A ReadinessEvaluation with a deterministic status.
        """
        if not parsed_extraction or not isinstance(parsed_extraction, dict):
            return ReadinessEvaluation(
                status=STATUS_INSUFFICIENT_INFORMATION,
                date_understood=False,
                guest_count_present=False,
                occasion_understood=False,
                meal_period_present=False,
                audience_identified=False,
                date_clarification_required=False,
                availability_check_possible=False,
                missing_for_availability=["extraction", "date", "guest_count"],
                notes="No extraction data available.",
            )

        ext = parsed_extraction

        # ── Evaluate each criterion ────────────────────────────────────────────

        date_request = ext.get("date_request") or {}
        dr_type: str = (date_request.get("date_request_type") or "unknown").lower()
        requires_clarification: bool = bool(
            date_request.get("requires_date_clarification", False)
        )

        date_understood: bool = (
            bool(date_request)
            and dr_type not in ("unknown", "")
            and not requires_clarification
        )

        guest_count = ext.get("guest_count")
        guest_count_present: bool = (
            guest_count is not None and str(guest_count).upper() != "NULL"
        )

        occasion = ext.get("occasion")
        occasion_understood: bool = bool(
            occasion
            and str(occasion).upper() not in ("NULL", "UNKNOWN", "OTHER", "")
        )

        meal_period = ext.get("meal_period")
        meal_period_present: bool = bool(
            meal_period
            and str(meal_period).upper() not in ("NULL", "UNKNOWN", "")
        )

        audience_type = ext.get("audience_type")
        audience_identified: bool = bool(
            audience_type
            and str(audience_type).upper() not in ("NULL", "UNKNOWN", "")
        )

        availability_check_possible: bool = (
            date_understood
            and guest_count_present
            and not requires_clarification
        )

        # ── Determine status ───────────────────────────────────────────────────

        missing: list[str] = []
        if not date_understood:
            missing.append("date")
        if not guest_count_present:
            missing.append("guest_count")

        if requires_clarification:
            # LLM explicitly flagged date as ambiguous — ask guest to clarify
            status = STATUS_NEEDS_CLARIFICATION
            notes = (
                "Date requires clarification from the guest: "
                + (date_request.get("clarification_question") or "date intent is ambiguous")
            )

        elif availability_check_possible:
            # All critical fields present — can proceed to availability check
            status = STATUS_READY_FOR_AVAILABILITY
            notes = "Date and guest count are understood; availability check is possible."

        elif date_understood and not guest_count_present:
            # Have a date but missing guest count — targeted clarification
            status = STATUS_NEEDS_CLARIFICATION
            notes = "Date understood but guest count is missing."

        elif not date_understood and not guest_count_present:
            # Nothing critical extracted — suggest structured webform
            if not any([occasion_understood, meal_period_present, audience_identified]):
                status = STATUS_INSUFFICIENT_INFORMATION
                notes = "No critical information extracted; cannot determine enquiry intent."
            else:
                status = STATUS_WEBFORM_REQUIRED
                notes = (
                    "Date and guest count are missing; some context was captured "
                    "but a structured webform would improve data quality."
                )

        else:
            # Have guest count but no date — targeted clarification
            status = STATUS_NEEDS_CLARIFICATION
            notes = "Guest count present but date is missing or not understood."

        return ReadinessEvaluation(
            status=status,
            date_understood=date_understood,
            guest_count_present=guest_count_present,
            occasion_understood=occasion_understood,
            meal_period_present=meal_period_present,
            audience_identified=audience_identified,
            date_clarification_required=requires_clarification,
            availability_check_possible=availability_check_possible,
            missing_for_availability=missing,
            notes=notes,
        )
