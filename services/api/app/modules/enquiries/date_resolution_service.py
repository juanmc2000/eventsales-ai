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
        anchor_date: date = request.anchor_date_override or self._parse_date(
            dr.get("anchor_date")
        ) or date.today()
        timezone: str = dr.get("timezone") or DEFAULT_TIMEZONE
        requires_clarification: bool = bool(dr.get("requires_date_clarification", False))
        clarification_question: str | None = self._null_str(dr.get("clarification_question"))
        confidence: float = self._coerce_float(dr.get("confidence"), default=0.0)

        # ── 2. Expand candidate dates ──────────────────────────────────────────
        candidate_dates, source_type = self._expand(dr, date_request_type, anchor_date)

        # ── 3. Persist EnquiryDateRequest ──────────────────────────────────────
        date_request_row = self._persist_date_request(
            request=request,
            raw_text=raw_text,
            date_request_type=date_request_type,
            anchor_date=anchor_date,
            timezone=timezone,
            extracted_json=dr,
            requires_date_clarification=requires_clarification,
            clarification_question=clarification_question,
            confidence=confidence,
        )
        date_request_id = date_request_row.id if date_request_row is not None else None

        # ── 4. Persist EnquiryCandidateDate rows ──────────────────────────────
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
            candidate_dates=candidate_dates,
            requires_date_clarification=requires_clarification,
            clarification_question=clarification_question,
        )

    # ── Expansion logic ───────────────────────────────────────────────────────

    def _expand(
        self,
        dr: dict,
        date_request_type: str,
        anchor_date: date,
    ) -> tuple[list[date], str]:
        """Expand the date_request dict into a list of candidate dates.

        Returns (candidate_dates, source_type).
        """
        try:
            if date_request_type == "exact":
                return self._expand_exact(dr, anchor_date), SOURCE_TYPE_EXPLICIT

            if date_request_type == "date_range":
                return self._expand_date_range(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type == "multiple_choice":
                return self._expand_multiple_choice(dr), SOURCE_TYPE_EXPLICIT

            if date_request_type == "month_flexible":
                return self._expand_month_flexible(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type == "weekday_range_over_relative_period":
                return self._expand_weekday_range(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type == "recurring_window":
                return self._expand_recurring_window(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type == "mixed_relative_dates":
                return self._expand_mixed_relative(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            if date_request_type == "ambiguous_numeric_date":
                # Store possible interpretations but require clarification — no expansion
                return self._expand_ambiguous(dr), SOURCE_TYPE_EXPLICIT

            if date_request_type == "relative_period":
                # The LLM occasionally uses this type instead of the canonical
                # "weekday_range_over_relative_period" or "exact".
                # When a single weekday is given, resolve to that weekday in the
                # next/this calendar week.  Multiple weekdays fall back to range.
                weekdays: list = dr.get("weekdays") or []
                if len(weekdays) == 1:
                    resolved = self._resolve_weekday_relative(
                        weekdays, dr.get("relative_period") or {}, anchor_date
                    )
                    return resolved[:1], SOURCE_TYPE_DETERMINISTIC
                return self._expand_weekday_range(dr, anchor_date), SOURCE_TYPE_DETERMINISTIC

            # unknown or unrecognised — no candidate dates
            return [], SOURCE_TYPE_DETERMINISTIC

        except Exception as exc:  # noqa: BLE001
            logger.warning("Date expansion failed for type %r: %s", date_request_type, exc)
            return [], SOURCE_TYPE_DETERMINISTIC

    def _expand_exact(self, dr: dict, anchor_date: date) -> list[date]:
        # 1. Explicit ISO dates
        explicit: list = dr.get("explicit_dates") or []
        if explicit:
            parsed = [self._parse_date(d) for d in explicit]
            return [d for d in parsed if d is not None][:1]  # single date
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
        start, end = self._resolve_relative_period(relative_period, anchor_date)

        results: list[date] = []
        current = start
        while current <= end and len(results) < MAX_CANDIDATE_DATES:
            if current.weekday() in target_weekdays:
                results.append(current)
            current += timedelta(days=1)
        return results

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
        anchor_date: date,
        timezone: str,
        extracted_json: dict,
        requires_date_clarification: bool,
        clarification_question: str | None,
        confidence: float,
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
                anchor_date=anchor_date,
                timezone=timezone,
                extracted_json=extracted_json,
                requires_date_clarification=requires_date_clarification,
                clarification_question=clarification_question,
                confidence=confidence if confidence is not None else None,
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
