"""Date Context Validator (ENQ-003).

Post-extraction validation that checks whether the date_request sub-object
contains sufficient context for reliable deterministic resolution.

The validator never modifies the extraction — it only produces diagnostic
warnings that are stored alongside the normalized extraction JSON and logged
for operational visibility.

Rules:
- Checks run on the date_request sub-dict from the LLM extraction output.
- A warning is emitted for each missing context field that is inferable or
  expected given the date_request_type.
- Warnings are stored as a list of strings in normalized_json under the key
  ``date_context_warnings``.
- No LLM calls are made.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Date request types that imply a month should be known
_MONTH_EXPECTED_TYPES = {
    "month_flexible",
    "date_range",
    "weekday_range_over_relative_period",
    "recurring_window",
    "mixed_relative_dates",
}

# Date request types that imply explicit date_range bounds should be populated
_RANGE_BOUNDS_EXPECTED_TYPES = {
    "date_range",
}

# Date request types that imply weekdays should be populated
_WEEKDAYS_EXPECTED_TYPES = {
    "weekday_range_over_relative_period",
    "recurring_window",
    "relative_period",
}

# Date request types that imply a relative_period should be populated
_RELATIVE_PERIOD_EXPECTED_TYPES = {
    "weekday_range_over_relative_period",
    "recurring_window",
    "relative_period",
    "month_flexible",  # e.g. "next August" has both month + relative_period
}


class DateContextValidator:
    """Validate date_request context and return diagnostic warnings.

    Usage::

        validator = DateContextValidator()
        warnings = validator.validate(date_request_dict)
        # → ["missing month: required for month_flexible resolution",
        #    "missing date_range.start_date: resolver cannot expand date window"]
    """

    def validate(self, date_request: dict | None) -> list[str]:
        """Return a list of diagnostic warning strings.

        Each warning identifies a missing or empty field that would impair
        deterministic date resolution.

        Args:
            date_request: The ``date_request`` sub-dict from the LLM extraction
                output, or ``None`` / ``{}`` when extraction produced no date.

        Returns:
            A (possibly empty) list of warning strings.  Always returns a list.
        """
        if not date_request or not isinstance(date_request, dict):
            return ["date_request is absent: deterministic resolution not possible"]

        warnings: list[str] = []
        dr_type: str = (date_request.get("date_request_type") or "unknown").strip().lower()

        # ── Month check ────────────────────────────────────────────────────────
        if dr_type in _MONTH_EXPECTED_TYPES:
            month = date_request.get("month")
            if month is None or str(month).upper() == "NULL":
                warnings.append(
                    f"missing month: expected for {dr_type!r} — "
                    "resolver cannot narrow the date window without a month value"
                )

        # ── Year check ─────────────────────────────────────────────────────────
        # Year is always useful when a month is given and is near a year boundary.
        # Flag when month is present but year is absent.
        month_val = date_request.get("month")
        year_val = date_request.get("year")
        if (
            month_val is not None
            and str(month_val).upper() != "NULL"
            and (year_val is None or str(year_val).upper() == "NULL")
        ):
            warnings.append(
                "missing year: month is present but year is absent — "
                "resolver will infer year from anchor date, which may be incorrect "
                "near year boundaries"
            )

        # ── Date range bounds check ────────────────────────────────────────────
        if dr_type in _RANGE_BOUNDS_EXPECTED_TYPES:
            date_range = date_request.get("date_range") or {}
            start = date_range.get("start_date")
            end = date_range.get("end_date")
            if not start or str(start).upper() == "NULL":
                warnings.append(
                    "missing date_range.start_date: resolver cannot expand the "
                    "date window without a start date"
                )
            if not end or str(end).upper() == "NULL":
                warnings.append(
                    "missing date_range.end_date: resolver cannot expand the "
                    "date window without an end date"
                )

        # ── Weekdays check ─────────────────────────────────────────────────────
        if dr_type in _WEEKDAYS_EXPECTED_TYPES:
            weekdays = date_request.get("weekdays") or []
            if not weekdays:
                warnings.append(
                    f"missing weekdays: expected for {dr_type!r} — "
                    "resolver cannot filter by day of week without weekday values"
                )

        # ── Relative period check ──────────────────────────────────────────────
        if dr_type in _RELATIVE_PERIOD_EXPECTED_TYPES:
            relative_period = date_request.get("relative_period") or {}
            direction = relative_period.get("direction")
            unit = relative_period.get("unit")
            if not direction or not unit:
                warnings.append(
                    f"missing relative_period context: expected for {dr_type!r} — "
                    "relative_period.direction and relative_period.unit should be set"
                )

        return warnings

    def validate_and_log(self, date_request: dict | None, enquiry_id=None) -> list[str]:
        """Validate and log all warnings.

        Args:
            date_request: The date_request sub-dict.
            enquiry_id: Optional enquiry ID for log context.

        Returns:
            The same list as ``validate()``.
        """
        warnings = self.validate(date_request)
        for warning in warnings:
            logger.warning(
                "Date context warning%s: %s",
                f" for enquiry {enquiry_id}" if enquiry_id else "",
                warning,
            )
        return warnings
