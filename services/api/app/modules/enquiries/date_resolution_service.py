"""Deterministic Date Resolution Service (WORKFLOW-008).

Reads the extracted date_request from the latest EnquiryExtraction for an enquiry,
creates an EnquiryDateRequest row, and deterministically expands the date intent
into EnquiryCandidateDate rows.

This service must NOT:
- Call any LLM or AI provider.
- Make pricing decisions.
- Check room availability.
- Write any customer-facing copy.

All date expansion is deterministic, testable, and auditable Python logic.

Default timezone: Europe/London
Candidate date cap: 60 dates
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.modules.enquiries.date_intent_normalizer import DateIntentNormalizer
from app.modules.enquiries.numeric_date_disambiguation_service import (
    DisambiguationResult,
    NumericDateDisambiguationService,
)

logger = logging.getLogger(__name__)

# Max candidate dates generated for a single date request
MAX_CANDIDATE_DATES = 60

# Default timezone when not provided by LLM
DEFAULT_TIMEZONE = "Europe/London"

# Source types stored on EnquiryCandidateDate rows
SOURCE_TYPE_EXPLICIT = "explicit"
SOURCE_TYPE_DETERMINISTIC = "deterministic"

# Lazy imports — models added by DATA-019
try:
    from app.modules.enquiries.models import EnquiryCandidateDate, EnquiryDateRequest  # noqa: F401
    _MODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MODELS_AVAILABLE = False
    EnquiryCandidateDate = None  # type: ignore[assignment,misc]
    EnquiryDateRequest = None  # type: ignore[assignment,misc]

# Lazy import — extraction model added by DATA-015
try:
    from app.modules.enquiries.models import EnquiryExtraction  # noqa: F401
    _EXTRACTION_AVAILABLE = True
except ImportError:  # pragma: no cover
    _EXTRACTION_AVAILABLE = False
    EnquiryExtraction = None  # type: ignore[assignment,misc]


# ── Request / Result dataclasses ──────────────────────────────────────────────


@dataclass
class DateResolutionRequest:
    """Input to the EnquiryDateResolutionService."""

    enquiry_id: uuid.UUID
    date_request_dict: dict   # The date_request sub-object from extraction parsed output
    tenant_id: str | None = field(default=None)
    extraction_id: uuid.UUID | None = field(default=None)
    prompt_run_id: uuid.UUID | None = field(default=None)
    # Optional reference date; defaults to today when None
    anchor_date_override: date | None = field(default=None)


@dataclass
class DateResolutionResult:
    """Output of the EnquiryDateResolutionService."""

    date_request_id: uuid.UUID | None
    date_request_type: str
    candidate_dates: list[date]
    requires_date_clarification: bool
    clarification_question: str | None = field(default=None)
    error_message: str | None = field(default=None)
    # ENQ-002: simplified normalized type (exact/range/recurring/ambiguous/unknown)
    date_request_type_normalized: str | None = field(default=None)
    # HOTFIX-001: numeric date disambiguation (None for non-numeric date types)
    ambiguity_type: str | None = field(default=None)
    assumed_date: date | None = field(default=None)
    alternative_date: date | None = field(default=None)
    ambiguity_clarification_required: bool = field(default=False)
    ambiguity_clarification_reason: str | None = field(default=None)
    ambiguity_clarification_question: str | None = field(default=None)


# ── Service ───────────────────────────────────────────────────────────────────


class EnquiryDateResolutionService:
    """Expands extracted date intent into deterministic candidate dates.

    Example::

        service = EnquiryDateResolutionService(db=db)
        result = service.resolve(DateResolutionRequest(
            enquiry_id=enquiry.id,
            date_request_dict={
                "date_request_type": "exact",
                "explicit_dates": ["2026-08-15"],
                "requires_date_clarification": False,
                "confidence": 0.95,
            },
        ))
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def resolve(self, request: DateResolutionRequest) -> DateResolutionResult:
        """Expand the date_request dict into candidate dates and persist rows.

        Always returns a DateResolutionResult — never raises.
        """
        dr = request.date_request_dict or {}

        # ── 1. Extract metadata ────────────────────────────────────────────────
        raw_text: str | None = self._null_str(dr.get("raw_text"))
        date_request_type: str = dr.get("date_request_type") or "unknown"
        # ENQ-002: compute simplified normalized type alongside raw type
        _normalizer = DateIntentNormalizer()
        date_request_type_normalized: str = _normalizer.normalise(date_request_type)
        anchor_date: date = request.anchor_date_override or self._parse_date(
            dr.get("anchor_date")
        ) or date.today()
        timezone: str = dr.get("timezone") or DEFAULT_TIMEZONE
        requires_clarification: bool = bool(dr.get("requires_date_clarification", False))
        clarification_question: str | None = self._null_str(dr.get("clarification_question"))
        confidence: float = self._coerce_float(dr.get("confidence"), default=0.0)

        # ── 2. Numeric date disambiguation (HOTFIX-001) ────────────────────────
        # Run before candidate expansion so the assumed_date can be used as the
        # primary candidate for ambiguous numeric dates.
        disambiguation: DisambiguationResult | None = None
        if date_request_type_normalized == "ambiguous":
            disambiguation = NumericDateDisambiguationService.from_raw_text(
                raw_text, anchor_date
            )

        # ── 3. Expand candidate dates ──────────────────────────────────────────
        # ENQ-002: resolver dispatches on normalized type for cleaner branching;
        # within each branch, structure of the dict (explicit_dates, date_range,
        # weekdays, month) determines the exact expansion strategy.
        candidate_dates, source_type = self._expand(
            dr, date_request_type, date_request_type_normalized, anchor_date,
            disambiguation=disambiguation,
        )

        # ── 4. Persist EnquiryDateRequest ──────────────────────────────────────
        date_request_row = self._persist_date_request(
            request=request,
            raw_text=raw_text,
            date_request_type=date_request_type,
            date_request_type_normalized=date_request_type_normalized,
            anchor_date=anchor_date,
            timezone=timezone,
            extracted_json=dr,
            requires_date_clarification=requires_clarification,
            clarification_question=clarification_question,
            confidence=confidence,
            disambiguation=disambiguation,
        )
        date_request_id = date_request_row.id if date_request_row is not None else None

        # ── 5. Persist EnquiryCandidateDate rows ──────────────────────────────
        if date_request_row is not None and candidate_dates:
            self._persist_candidate_dates(
                enquiry_id=request.enquiry_id,
                date_request_id=date_request_id,
                tenant_id=request.tenant_id,
                candidate_dates=candidate_dates,
                source_type=source_type,
            )

        return DateResolutionResult(
            date_request_id=date_request_id,
            date_request_type=date_request_type,
            date_request_type_normalized=date_request_type_normalized,
            candidate_dates=candidate_dates,
            requires_date_clarification=requires_clarification,
            clarification_question=clarification_question,
            ambiguity_type=disambiguation.ambiguity_type if disambiguation else None,
            assumed_date=disambiguation.assumed_date if disambiguation else None,
            alternative_date=disambiguation.alternative_date if disambiguation else None,
            ambiguity_clarification_required=disambiguation.clarification_required if disambiguation else False,
            ambiguity_clarification_reason=disambiguation.clarification_reason if disambiguation else None,
            ambiguity_clarification_question=disambiguation.clarification_question if disambiguation else None,
        )

    # ── Expansion logic ───────────────────────────────────────────────────────

    def _expand(
        self,
        dr: dict,
        date_request_type: str,
        date_request_type_normalized: str,
        anchor_date: date,
        disambiguation: DisambiguationResult | None = None,
    ) -> tuple[list[date], str]:
        """Expand the date_request dict into a list of candidate dates.

        ENQ-002: dispatches on the normalized type (exact/range/recurring/
        ambiguous/unknown).  Within each branch, the structure of the dict
        (explicit_dates, date_range, weekdays, month) determines the exact
        expansion strategy, so no information is lost by the simplification.

        Returns (candidate_dates, source_type).
        """
        try:
            if date_request_type_normalized == "exact":
                return self._expand_exact(dr, anchor_date), SOURCE_TYPE_EXPLICIT

            if date_request_type_normalized == "range":
                return self._expand_range(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type_normalized == "recurring":
                return self._expand_recurring(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type_normalized == "ambiguous":
                # HOTFIX-001: if numeric disambiguation resolved to an assumed date,
                # use that as the single candidate so availability can be checked.
                if disambiguation is not None and disambiguation.assumed_date is not None:
                    return [disambiguation.assumed_date], SOURCE_TYPE_DETERMINISTIC
                return self._expand_ambiguous(dr), SOURCE_TYPE_EXPLICIT

            # unknown or unrecognised — no candidate dates
            return [], SOURCE_TYPE_DETERMINISTIC

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Date expansion failed for raw type %r (normalized: %r): %s",
                date_request_type, date_request_type_normalized, exc,
            )
            return [], SOURCE_TYPE_DETERMINISTIC

    def _expand_exact(self, dr: dict, anchor_date: date) -> list[date]:
        # 1. Explicit ISO dates
        explicit: list = dr.get("explicit_dates") or []
        if explicit:
            parsed = [d for d in (self._parse_date(x) for x in explicit) if d is not None]
            # HOTFIX-002: When the LLM sets direction="next" + weekdays, it sometimes
            # pre-computes explicit_dates as the CURRENT week's occurrence rather than
            # next week's (e.g. "next Saturday" from Wed Jun 3 → LLM gives Jun 6 which
            # is this Saturday, but British "next" means the following week = Jun 13).
            # If the explicit date falls inside the current calendar week AND weekdays +
            # direction="next" are also present, override with _resolve_weekday_relative.
            weekdays_check: list = dr.get("weekdays") or []
            rp_check = dr.get("relative_period") or {}
            if (
                parsed
                and weekdays_check
                and (rp_check.get("direction") or "").lower() == "next"
            ):
                monday_of_this_week = anchor_date - timedelta(days=anchor_date.weekday())
                sunday_of_this_week = monday_of_this_week + timedelta(days=6)
                if monday_of_this_week <= parsed[0] <= sunday_of_this_week:
                    resolved = self._resolve_weekday_relative(
                        weekdays_check, rp_check, anchor_date
                    )
                    if resolved:
                        return resolved[:1]
            if parsed:
                return parsed[:1]  # single date
        # 2. anchor_date embedded in the extraction JSON
        anchor = self._parse_date(dr.get("anchor_date"))
        if anchor:
            return [anchor]
        # 3. Weekday + relative_period fallback — e.g. "next Wednesday"
        #    The LLM sometimes sets type="exact" but expresses the date via
        #    weekdays + relative_period instead of explicit_dates.
        weekdays: list = dr.get("weekdays") or []
        relative_period = dr.get("relative_period") or {}
        if weekdays:
            resolved = self._resolve_weekday_relative(
                weekdays, relative_period, anchor_date
            )
            if resolved:
                return resolved[:1]
        return []

    def _resolve_weekday_relative(
        self,
        weekdays: list,
        relative_period: dict,
        anchor_date: date,
    ) -> list[date]:
        """Resolve a single weekday + relative_period to a concrete date.

        "next Wednesday" semantics: Wednesday of the NEXT calendar week
        (i.e. Monday-anchored week following the anchor date's week).
        This matches British English convention where "next Wednesday"
        always means the week after the current one.
        """
        target_weekday = self._parse_weekday(weekdays[0] if weekdays else None)
        if target_weekday is None:
            return []

        direction = (relative_period.get("direction") or "next").lower()

        if direction == "next":
            # Advance to the Monday that starts NEXT week, then add weekday offset.
            # anchor.weekday() == 0 (Mon) → +7 days to reach next Monday.
            days_to_next_monday = 7 - anchor_date.weekday()
            start_of_next_week = anchor_date + timedelta(days=days_to_next_monday)
            return [start_of_next_week + timedelta(days=target_weekday)]

        if direction == "this":
            # Monday of the CURRENT week, then add weekday offset.
            start_of_this_week = anchor_date - timedelta(days=anchor_date.weekday())
            target = start_of_this_week + timedelta(days=target_weekday)
            return [target] if target >= anchor_date else []

        # last / other — fall back to range search
        start, end = self._resolve_relative_period(relative_period, anchor_date)
        current = start
        while current <= end:
            if current.weekday() == target_weekday:
                return [current]
            current += timedelta(days=1)
        return []

    def _expand_range(self, dr: dict, anchor_date: date) -> list[date]:
        """Expand any 'range' normalized type into candidate dates.

        Uses structural heuristics on the date_request dict to pick the right
        sub-expansion, so no context is lost when dispatching on normalized type:
        1. date_range with start/end bounds → date_range expansion
        2. Multiple explicit dates → multiple_choice expansion
        3. month present → month_flexible expansion
        4. weekdays present → weekday_range expansion
        5. Single explicit date → treat as a single-date multiple_choice
        """
        date_range = dr.get("date_range") or {}
        if date_range.get("start_date") or date_range.get("end_date"):
            return self._expand_date_range(dr, anchor_date)

        explicit: list = dr.get("explicit_dates") or []
        if len(explicit) > 1:
            return self._expand_multiple_choice(dr)

        if dr.get("month"):
            return self._expand_month_flexible(dr, anchor_date)

        if dr.get("weekdays"):
            return self._expand_weekday_range(dr, anchor_date)

        if len(explicit) == 1:
            return self._expand_multiple_choice(dr)

        return []

    def _expand_recurring(self, dr: dict, anchor_date: date) -> list[date]:
        """Expand any 'recurring' normalized type into candidate dates.

        Uses structural heuristics:
        1. Has explicit_dates → mixed_relative expansion
        2. Has weekdays → weekday_range expansion (covers weekday_range and recurring_window)
        3. Single weekday in relative_period → weekday_relative resolution
        """
        explicit: list = dr.get("explicit_dates") or []
        weekdays: list = dr.get("weekdays") or []

        if explicit:
            return self._expand_mixed_relative(dr, anchor_date)

        if len(weekdays) == 1:
            # "next Wednesday" type patterns: resolve to single weekday in next week.
            # ENQ-006: skip this short-circuit when relative_period has no direction
            # but date_range bounds are available — _expand_weekday_range will use
            # the date_range window instead of defaulting to next-week resolution.
            relative_period = dr.get("relative_period") or {}
            rp_direction = (relative_period.get("direction") or "").strip().lower()
            date_range_obj = dr.get("date_range") or {}
            use_date_range_fallback = (
                not rp_direction
                and bool(date_range_obj.get("start_date"))
                and bool(date_range_obj.get("end_date"))
            )
            if not use_date_range_fallback:
                resolved = self._resolve_weekday_relative(
                    weekdays, relative_period, anchor_date
                )
                if resolved:
                    return resolved[:1]

        if weekdays:
            return self._expand_weekday_range(dr, anchor_date)

        return []

    def _expand_date_range(self, dr: dict, anchor_date: date) -> list[date]:
        date_range = dr.get("date_range") or {}
        start = self._parse_date(date_range.get("start_date"))
        end = self._parse_date(date_range.get("end_date"))
        if start is None or end is None:
            return []
        if end < start:
            start, end = end, start
        return self._date_range_list(start, end)

    def _expand_multiple_choice(self, dr: dict) -> list[date]:
        explicit: list = dr.get("explicit_dates") or []
        parsed = [self._parse_date(d) for d in explicit]
        return [d for d in parsed if d is not None][:MAX_CANDIDATE_DATES]

    def _expand_month_flexible(self, dr: dict, anchor_date: date) -> list[date]:
        month: int | None = self._coerce_int(dr.get("month"))
        year: int | None = self._coerce_int(dr.get("year"))

        if month is None:
            return []

        # If no year, use current or next year depending on whether the month has passed
        if year is None:
            year = anchor_date.year
            if month < anchor_date.month:
                year += 1

        # Generate all dates in the month
        first = date(year, month, 1)
        if month == 12:
            last = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        return self._date_range_list(first, last)

    def _expand_weekday_range(self, dr: dict, anchor_date: date) -> list[date]:
        weekdays: list = dr.get("weekdays") or []
        if not weekdays:
            return []

        target_weekdays = {self._parse_weekday(w) for w in weekdays}
        target_weekdays.discard(None)  # type: ignore[arg-type]
        if not target_weekdays:
            return []

        relative_period = dr.get("relative_period") or {}

        # ENQ-006: When relative_period has no direction, fall back to date_range
        # bounds (start_date + end_date) as the expansion window.  This handles LLM
        # output where the date window is expressed via date_range only (e.g.
        # "any Friday in August" → date_range=2026-08-01..2026-08-31) without a
        # relative_period direction that the resolver can use for window calculation.
        rp_direction = (relative_period.get("direction") or "").strip().lower()
        if not rp_direction:
            date_range = dr.get("date_range") or {}
            range_start = self._parse_date(date_range.get("start_date"))
            range_end = self._parse_date(date_range.get("end_date"))
            if range_start is not None and range_end is not None:
                # Clamp to anchor_date — never return dates in the past.
                # Always return from this branch; do not fall through to
                # _resolve_relative_period when date_range bounds are present.
                start = max(range_start, anchor_date)
                end = range_end
                if start > end:
                    return []
                return self._collect_weekdays_in_window(target_weekdays, start, end)

        start, end = self._resolve_relative_period(relative_period, anchor_date)
        return self._collect_weekdays_in_window(target_weekdays, start, end)

    def _expand_recurring_window(self, dr: dict, anchor_date: date) -> list[date]:
        # Treat like weekday_range — recurring windows are defined by weekday + period
        return self._expand_weekday_range(dr, anchor_date)

    def _expand_mixed_relative(self, dr: dict, anchor_date: date) -> list[date]:
        # Combine explicit_dates with any weekday expansion
        results: list[date] = list(self._expand_multiple_choice(dr))
        results += self._expand_weekday_range(dr, anchor_date)
        # Deduplicate and sort
        return sorted(set(results))[:MAX_CANDIDATE_DATES]

    def _expand_ambiguous(self, dr: dict) -> list[date]:
        """For ambiguous dates, extract possible interpretations without choosing one."""
        ambiguous_dates: list = dr.get("ambiguous_dates") or []
        results: list[date] = []
        for entry in ambiguous_dates:
            if isinstance(entry, dict):
                for possible in entry.get("possible_dates") or []:
                    parsed = self._parse_date(possible)
                    if parsed is not None:
                        results.append(parsed)
        return sorted(set(results))[:MAX_CANDIDATE_DATES]

    # ── Persistence helpers ───────────────────────────────────────────────────

    def _persist_date_request(
        self,
        request: DateResolutionRequest,
        raw_text: str | None,
        date_request_type: str,
        date_request_type_normalized: str,
        anchor_date: date,
        timezone: str,
        extracted_json: dict,
        requires_date_clarification: bool,
        clarification_question: str | None,
        confidence: float,
        disambiguation: DisambiguationResult | None = None,
    ):
        if not _MODELS_AVAILABLE or EnquiryDateRequest is None:
            logger.warning(
                "EnquiryDateRequest model not available — skipping persistence"
            )
            return None
        try:
            row = EnquiryDateRequest(
                id=uuid.uuid4(),
                tenant_id=request.tenant_id,
                enquiry_id=request.enquiry_id,
                extraction_id=request.extraction_id,
                prompt_run_id=request.prompt_run_id,
                raw_text=raw_text,
                date_request_type=date_request_type,
                date_request_type_normalized=date_request_type_normalized,
                anchor_date=anchor_date,
                timezone=timezone,
                extracted_json=extracted_json,
                requires_date_clarification=requires_date_clarification,
                clarification_question=clarification_question,
                confidence=confidence if confidence is not None else None,
                ambiguity_type=disambiguation.ambiguity_type if disambiguation else None,
                assumed_date=disambiguation.assumed_date if disambiguation else None,
                alternative_date=disambiguation.alternative_date if disambiguation else None,
                clarification_required=disambiguation.clarification_required if disambiguation else None,
                clarification_reason=disambiguation.clarification_reason if disambiguation else None,
            )
            self._db.add(row)
            self._db.flush()
            return row
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist EnquiryDateRequest for enquiry %s: %s",
                request.enquiry_id,
                exc,
            )
            return None

    def _persist_candidate_dates(
        self,
        enquiry_id: uuid.UUID,
        date_request_id: uuid.UUID,
        tenant_id: str | None,
        candidate_dates: list[date],
        source_type: str,
    ) -> None:
        if not _MODELS_AVAILABLE or EnquiryCandidateDate is None:
            logger.warning(
                "EnquiryCandidateDate model not available — skipping persistence"
            )
            return
        try:
            for candidate in candidate_dates[:MAX_CANDIDATE_DATES]:
                row = EnquiryCandidateDate(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    enquiry_id=enquiry_id,
                    date_request_id=date_request_id,
                    candidate_date=candidate,
                    source_type=source_type,
                    availability_status=None,
                    pricing_checked=False,
                    recommended_minimum_spend=None,
                    ranking_score=None,
                )
                self._db.add(row)
            self._db.flush()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist candidate dates for enquiry %s: %s",
                enquiry_id,
                exc,
            )

    # ── Static helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value or not isinstance(value, str):
            return None
        val = value.strip()
        if val.upper() == "NULL" or not val:
            return None
        try:
            return date.fromisoformat(val[:10])
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _null_str(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, str) and value.strip().upper() == "NULL":
            return None
        return value if value else None

    @staticmethod
    def _coerce_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_float(value, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_weekday(name: str | None) -> int | None:
        """Convert weekday name to Python weekday integer (Monday=0, Sunday=6)."""
        if not name or not isinstance(name, str):
            return None
        mapping = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        return mapping.get(name.strip().lower())

    @staticmethod
    def _resolve_relative_period(
        relative_period: dict,
        anchor_date: date,
    ) -> tuple[date, date]:
        """Resolve a relative period dict to (start_date, end_date).

        Defaults: direction=next, unit=week, amount=1
        """
        direction = (relative_period.get("direction") or "next").lower()
        unit = (relative_period.get("unit") or "week").lower()
        amount: int = EnquiryDateResolutionService._coerce_int(
            relative_period.get("amount")
        ) or 1

        # For "next/this/last week" snap to calendar-week (Mon–Sun) boundaries so
        # that "next week" always means the following Mon–Sun regardless of what
        # day of the week the anchor falls on.  All other units use the rolling
        # window below.
        if unit == "week" and direction in ("next", "this", "last"):
            monday_of_this_week = anchor_date - timedelta(days=anchor_date.weekday())
            if direction == "next":
                start = monday_of_this_week + timedelta(weeks=1)
                end = start + timedelta(weeks=amount) - timedelta(days=1)
            elif direction == "this":
                start = monday_of_this_week
                end = start + timedelta(weeks=amount) - timedelta(days=1)
            else:  # last
                end = monday_of_this_week - timedelta(days=1)
                start = end - timedelta(weeks=amount) + timedelta(days=1)
            return start, end

        unit_days = {"day": 1, "week": 7, "month": 30, "year": 365}
        delta_days = unit_days.get(unit, 7) * amount

        if direction == "last":
            end = anchor_date - timedelta(days=1)
            start = end - timedelta(days=delta_days - 1)
        elif direction == "this":
            start = anchor_date
            end = anchor_date + timedelta(days=delta_days - 1)
        else:  # next (default)
            start = anchor_date + timedelta(days=1)
            end = start + timedelta(days=delta_days - 1)

        return start, end

    @staticmethod
    def _date_range_list(start: date, end: date) -> list[date]:
        """Return all dates from start to end inclusive, capped at MAX_CANDIDATE_DATES."""
        results: list[date] = []
        current = start
        while current <= end and len(results) < MAX_CANDIDATE_DATES:
            results.append(current)
            current += timedelta(days=1)
        return results

    @staticmethod
    def _collect_weekdays_in_window(
        target_weekdays: set[int],
        start: date,
        end: date,
    ) -> list[date]:
        """Return all dates in [start, end] whose weekday is in target_weekdays.

        Capped at MAX_CANDIDATE_DATES.
        """
        results: list[date] = []
        current = start
        while current <= end and len(results) < MAX_CANDIDATE_DATES:
            if current.weekday() in target_weekdays:
                results.append(current)
            current += timedelta(days=1)
        return results
