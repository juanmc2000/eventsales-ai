"""Deterministic Enquiry Processing Service (WORKFLOW-007).

Consumes a structured extraction result and applies rule-based logic to
produce availability, room suitability, pricing, missing-field, and
recommended-action outputs.

This service must NOT:
- Call any LLM or AI provider.
- Make customer-facing drafting decisions.
- Use probabilistic or ML-based matching.

All decisions are deterministic, testable, and auditable.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.modules.pricing.schemas import PricingRecommendationRequest
from app.modules.pricing.service import PricingRuleService
from app.modules.restaurants.repository import RoomAvailabilityRepository, RoomRepository
from app.modules.enquiries.repository import DateRequestRepository

# EnquiryProcessingSnapshot is added by DATA-015.  Use a lazy import.
try:
    from app.modules.enquiries.models import EnquiryProcessingSnapshot
except ImportError:  # pragma: no cover
    EnquiryProcessingSnapshot = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ── Recommended action constants ──────────────────────────────────────────────

ACTION_SEND_CONFIRMATION = "send_availability_confirmation"
ACTION_SEND_WITH_QUESTIONS = "send_availability_with_missing_info_question"
ACTION_REQUEST_INFO = "request_missing_information"
ACTION_SUGGEST_ALTERNATIVE = "suggest_alternative_room"
ACTION_ESCALATE = "escalate_to_human"
ACTION_UNABLE = "unable_to_process"

ALL_ACTIONS = {
    ACTION_SEND_CONFIRMATION,
    ACTION_SEND_WITH_QUESTIONS,
    ACTION_REQUEST_INFO,
    ACTION_SUGGEST_ALTERNATIVE,
    ACTION_ESCALATE,
    ACTION_UNABLE,
}

# Fields considered critical — absence means we cannot proceed without asking
CRITICAL_FIELDS = {"guest_count", "event_date"}

# Meal period inference thresholds (24-hour clock)
_LUNCH_CUTOFF_HOUR = 15     # before 15:00 → lunch
_DINNER_START_HOUR = 15     # 15:00+ → dinner


# ── Request / Result dataclasses ──────────────────────────────────────────────


@dataclass
class ProcessingRequest:
    """Input to the EnquiryProcessingService."""

    enquiry_id: uuid.UUID
    restaurant_id: uuid.UUID
    extraction_id: uuid.UUID
    extraction_parsed: dict  # validated extraction output from EnquiryExtractionOutput
    tenant_id: str | None = field(default=None)


@dataclass
class ProcessingResult:
    """Output of the EnquiryProcessingService.

    snapshot_id is set when the row was persisted successfully.
    All JSON fields mirror the enquiry_processing_snapshots columns.
    candidate_date_summary is populated when candidate dates were processed.
    """

    snapshot_id: uuid.UUID | None
    recommended_action: str
    availability_result_json: dict | None = field(default=None)
    room_suitability_json: dict | None = field(default=None)
    pricing_result_json: dict | None = field(default=None)
    missing_fields_json: list[str] | None = field(default=None)
    error_message: str | None = field(default=None)
    # Populated when candidate dates exist
    candidate_date_summary: dict | None = field(default=None)


# ── Service ───────────────────────────────────────────────────────────────────


class EnquiryProcessingService:
    """Applies deterministic processing to an extraction result.

    Example::

        service = EnquiryProcessingService(db=db)
        result = service.process(ProcessingRequest(
            enquiry_id=enquiry.id,
            restaurant_id=restaurant.id,
            extraction_id=extraction.id,
            extraction_parsed={"guest_count": 20, "event_date": "2026-12-25", ...},
        ))
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._room_repo = RoomRepository(db)
        self._avail_repo = RoomAvailabilityRepository(db)
        self._pricing_svc = PricingRuleService(db)
        self._date_request_repo = DateRequestRepository(db)

    def process(self, request: ProcessingRequest) -> ProcessingResult:
        """Run deterministic processing and persist the snapshot.

        Always returns a ProcessingResult — never raises.
        """
        extraction = request.extraction_parsed or {}

        # ── 1. Identify missing and critical fields ────────────────────────────
        extraction_missing: list[str] = extraction.get("missing_fields") or []
        missing_fields = list(extraction_missing)

        guest_count: int | None = self._coerce_int(extraction.get("guest_count"))
        event_date_str: str | None = extraction.get("event_date")
        event_date: date | None = self._parse_date(event_date_str)
        event_time: str | None = extraction.get("event_time")

        if guest_count is None and "guest_count" not in missing_fields:
            missing_fields.append("guest_count")
        if event_date is None and "event_date" not in missing_fields:
            missing_fields.append("event_date")

        # ── 2. Room suitability ────────────────────────────────────────────────
        rooms = self._room_repo.list_for_restaurant(request.restaurant_id)
        preferred_area: str | None = self._extract_preferred_area(extraction)
        matched_room = _match_room(rooms, guest_count, preferred_area)

        room_suitability = self._build_room_suitability(matched_room, guest_count)

        # ── 3. Availability check ──────────────────────────────────────────────
        availability_result: dict | None = None
        if matched_room is not None and event_date is not None:
            meal_period = self._infer_meal_period(event_time)
            availability_result = self._check_availability(
                matched_room.id, event_date, meal_period
            )
        elif matched_room is not None:
            availability_result = {
                "status": "unknown",
                "reason": "event_date not available — cannot check availability",
            }

        # ── 4. Pricing ────────────────────────────────────────────────────────
        pricing_result: dict | None = None
        pricing_rule_id: uuid.UUID | None = None
        if event_date is not None:
            meal_period_for_pricing = self._infer_meal_period(event_time)
            pricing_result, pricing_rule_id = self._calculate_pricing(
                restaurant_id=request.restaurant_id,
                event_date=event_date,
                meal_period=meal_period_for_pricing,
                guest_count=guest_count,
            )

        # ── 5. Candidate date processing ───────────────────────────────────────
        candidate_date_summary: dict | None = None
        date_request_row = self._date_request_repo.get_latest_date_request(
            request.enquiry_id
        )

        if date_request_row is not None:
            candidate_date_summary = self._process_candidate_dates(
                date_request_row=date_request_row,
                matched_room=matched_room,
                event_time=event_time,
                restaurant_id=request.restaurant_id,
            )
            # If clarification is required due to date ambiguity, override action
            if isinstance(date_request_row.requires_date_clarification, bool) and date_request_row.requires_date_clarification:
                missing_fields = list(missing_fields)
                if "event_date" not in missing_fields:
                    missing_fields.append("event_date")

        # ── 6. Recommended action ─────────────────────────────────────────────
        # When candidate dates exist and one is available, refine availability_result
        if candidate_date_summary is not None:
            available_dates = candidate_date_summary.get("available_candidate_dates") or []
            recommended_candidate = candidate_date_summary.get("recommended_candidate_date")
            requires_clarification = candidate_date_summary.get("requires_date_clarification", False)

            if requires_clarification:
                # Ambiguous date — must ask guest to clarify
                recommended_action = ACTION_REQUEST_INFO
            elif recommended_candidate and matched_room:
                # We have an available candidate date and a room — synthesize availability
                availability_result = {
                    "status": "available",
                    "date": recommended_candidate,
                    "meal_period": self._infer_meal_period(event_time),
                    "source": "candidate_date_check",
                }
                recommended_action = self._recommend_action(
                    missing_fields=missing_fields,
                    matched_room=matched_room,
                    availability_result=availability_result,
                )
            elif available_dates:
                recommended_action = self._recommend_action(
                    missing_fields=missing_fields,
                    matched_room=matched_room,
                    availability_result={"status": "available"},
                )
            else:
                recommended_action = self._recommend_action(
                    missing_fields=missing_fields,
                    matched_room=matched_room,
                    availability_result=availability_result,
                )
        else:
            recommended_action = self._recommend_action(
                missing_fields=missing_fields,
                matched_room=matched_room,
                availability_result=availability_result,
            )

        # ── 7. Persist snapshot ────────────────────────────────────────────────
        snapshot = self._persist_snapshot(
            request=request,
            pricing_rule_id=pricing_rule_id,
            availability_result_json=availability_result,
            room_suitability_json=room_suitability,
            pricing_result_json=pricing_result,
            missing_fields_json=missing_fields if missing_fields else None,
            recommended_action=recommended_action,
            candidate_date_summary=candidate_date_summary,
        )

        return ProcessingResult(
            snapshot_id=snapshot.id if snapshot is not None else None,
            recommended_action=recommended_action,
            availability_result_json=availability_result,
            room_suitability_json=room_suitability,
            pricing_result_json=pricing_result,
            missing_fields_json=missing_fields if missing_fields else None,
            candidate_date_summary=candidate_date_summary,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_room_suitability(self, room, guest_count: int | None) -> dict | None:
        if room is None:
            return {"matched": False, "reason": "No suitable room found for this restaurant"}
        result: dict = {
            "matched": True,
            "room_id": str(room.id),
            "room_name": room.name,
            "room_type": room.room_type,
            "seated_capacity": room.seated_capacity,
            "is_private_dining": room.is_private_dining,
        }
        if guest_count is not None and room.seated_capacity:
            result["capacity_suitable"] = guest_count <= room.seated_capacity
        else:
            result["capacity_suitable"] = None
        return result

    def _check_availability(
        self, room_id: uuid.UUID, event_date: date, meal_period: str
    ) -> dict:
        slots = self._avail_repo.get_for_room_date(room_id, event_date)
        if not slots:
            return {
                "status": "unknown",
                "date": event_date.isoformat(),
                "meal_period": meal_period,
                "reason": "No availability data for this date",
            }

        # Find the slot matching the requested meal period
        slot = next((s for s in slots if s.meal_period == meal_period), None)
        if slot is None:
            slot = slots[0]  # fallback to first slot

        return {
            "status": slot.status,
            "date": event_date.isoformat(),
            "meal_period": slot.meal_period,
            "notes": slot.notes,
        }

    def _calculate_pricing(
        self,
        restaurant_id: uuid.UUID,
        event_date: date,
        meal_period: str,
        guest_count: int | None,
    ) -> tuple[dict | None, uuid.UUID | None]:
        try:
            rec = self._pricing_svc.calculate_recommendation(
                PricingRecommendationRequest(
                    restaurant_id=restaurant_id,
                    day_of_week=event_date.weekday(),
                    meal_period=meal_period,
                    party_size=guest_count,
                )
            )
            rule_id: uuid.UUID | None = None
            if rec.applied_rules:
                rule_id = rec.applied_rules[0].rule_id
            return {
                "minimum_spend": rec.recommended_minimum_spend,
                "explanation": rec.explanation,
                "confidence": rec.confidence,
            }, rule_id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pricing calculation failed: %s", exc)
            return None, None

    def _recommend_action(
        self,
        missing_fields: list[str],
        matched_room,
        availability_result: dict | None,
    ) -> str:
        critical_missing = [f for f in missing_fields if f in CRITICAL_FIELDS]

        if matched_room is None:
            return ACTION_SUGGEST_ALTERNATIVE

        if len(critical_missing) >= 2:
            # Both guest_count and event_date are missing — cannot proceed
            return ACTION_REQUEST_INFO

        avail_status = (availability_result or {}).get("status")

        if avail_status == "available":
            if missing_fields:
                return ACTION_SEND_WITH_QUESTIONS
            return ACTION_SEND_CONFIRMATION

        if avail_status in ("booked", "held", "unavailable"):
            return ACTION_SUGGEST_ALTERNATIVE

        if avail_status == "unknown":
            if critical_missing:
                return ACTION_REQUEST_INFO
            return ACTION_ESCALATE

        # No availability data — event_date was missing
        if critical_missing:
            return ACTION_REQUEST_INFO
        return ACTION_ESCALATE

    def _process_candidate_dates(
        self,
        date_request_row,
        matched_room,
        event_time: str | None,
        restaurant_id: uuid.UUID,
    ) -> dict:
        """Check availability and pricing for all candidate dates.

        Updates EnquiryCandidateDate rows in place.
        Returns a summary dict for inclusion in the processing snapshot.
        """
        candidates = self._date_request_repo.list_candidate_dates_for_request(
            date_request_row.id
        )

        if not candidates:
            return {
                "candidate_dates_checked": 0,
                "available_candidate_dates": [],
                "unavailable_candidate_dates": [],
                "recommended_candidate_date": None,
                "requires_date_clarification": bool(
                    isinstance(date_request_row.requires_date_clarification, bool)
                    and date_request_row.requires_date_clarification
                ),
                "clarification_question": date_request_row.clarification_question,
            }

        meal_period = self._infer_meal_period(event_time)
        available: list[str] = []
        unavailable: list[str] = []
        recommended: str | None = None

        for candidate in candidates:
            candidate_date = candidate.candidate_date
            avail_status: str | None = None
            spend: float | None = None
            pricing_checked = False

            if matched_room is not None:
                avail = self._check_availability(matched_room.id, candidate_date, meal_period)
                avail_status = avail.get("status")

                if avail_status == "available":
                    available.append(candidate_date.isoformat())
                    # Calculate pricing for available dates
                    pricing_result, _ = self._calculate_pricing(
                        restaurant_id=restaurant_id,
                        event_date=candidate_date,
                        meal_period=meal_period,
                        guest_count=None,
                    )
                    pricing_checked = True
                    if pricing_result:
                        spend = pricing_result.get("minimum_spend")
                    # Track the first available date as recommended
                    if recommended is None:
                        recommended = candidate_date.isoformat()
                else:
                    unavailable.append(candidate_date.isoformat())
            else:
                avail_status = "unknown"
                unavailable.append(candidate_date.isoformat())

            # Update the candidate row
            try:
                self._date_request_repo.update_candidate_date(
                    candidate=candidate,
                    availability_status=avail_status,
                    pricing_checked=pricing_checked,
                    recommended_minimum_spend=spend,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to update candidate date %s: %s", candidate.id, exc)

        requires_clarification = bool(
            isinstance(date_request_row.requires_date_clarification, bool)
            and date_request_row.requires_date_clarification
        )

        return {
            "candidate_dates_checked": len(candidates),
            "available_candidate_dates": available,
            "unavailable_candidate_dates": unavailable,
            "recommended_candidate_date": recommended,
            "requires_date_clarification": requires_clarification,
            "clarification_question": date_request_row.clarification_question,
        }

    def _persist_snapshot(
        self,
        request: ProcessingRequest,
        pricing_rule_id: uuid.UUID | None,
        availability_result_json: dict | None,
        room_suitability_json: dict | None,
        pricing_result_json: dict | None,
        missing_fields_json: list[str] | None,
        recommended_action: str,
        candidate_date_summary: dict | None = None,
    ):
        try:
            if EnquiryProcessingSnapshot is None:  # DATA-015 not yet applied
                logger.warning(
                    "EnquiryProcessingSnapshot model not available — skipping persistence"
                )
                return None

            # Merge candidate date summary into availability_result_json when present
            merged_avail = dict(availability_result_json) if availability_result_json else {}
            if candidate_date_summary:
                merged_avail["candidate_date_summary"] = candidate_date_summary

            snapshot = EnquiryProcessingSnapshot(
                id=uuid.uuid4(),
                tenant_id=request.tenant_id,
                enquiry_id=request.enquiry_id,
                extraction_id=request.extraction_id,
                pricing_rule_id=pricing_rule_id,
                availability_result_json=merged_avail if merged_avail else None,
                room_suitability_json=room_suitability_json,
                pricing_result_json=pricing_result_json,
                missing_fields_json=missing_fields_json,
                recommended_action=recommended_action,
            )
            self._db.add(snapshot)
            self._db.flush()
            return snapshot
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist processing snapshot for enquiry %s: %s",
                request.enquiry_id,
                exc,
            )
            return None

    @staticmethod
    def _coerce_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _infer_meal_period(event_time: str | None) -> str:
        """Infer meal period from time string (HH:MM).  Default: dinner."""
        if not event_time:
            return "dinner"
        try:
            hour = int(event_time.split(":")[0])
            return "lunch" if hour < _LUNCH_CUTOFF_HOUR else "dinner"
        except (ValueError, IndexError):
            return "dinner"

    @staticmethod
    def _extract_preferred_area(extraction: dict) -> str | None:
        """Look for preferred room/area hints in the extraction output."""
        notes: str | None = extraction.get("freeform_notes")
        if notes and "private" in notes.lower():
            return "private"
        return None


# ── Room matching (deterministic) ─────────────────────────────────────────────


def _match_room(rooms: list, party_size: int | None, preferred_area: str | None):
    """Select the most suitable room deterministically.

    Priority:
    1. Preferred area / name match (case-insensitive substring).
    2. First room whose seated_capacity >= party_size (ascending by display_order).
    3. First active room.
    4. None if no rooms.
    """
    if not rooms:
        return None

    if preferred_area:
        term = preferred_area.strip().lower()
        for room in rooms:
            if term in room.name.lower():
                return room

    if party_size is not None:
        for room in rooms:
            capacity = room.seated_capacity or 0
            if capacity >= party_size:
                return room

    return rooms[0]
