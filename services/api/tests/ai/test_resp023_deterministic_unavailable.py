"""Tests for RESP-023 — Deterministic RESPOND_UNAVAILABLE draft generation.

Verifies that when response_goal is RESPOND_UNAVAILABLE:
- The LLM (AIGateway) is never called.
- The draft body is built from FirstResponseCopyLibrary copy blocks only.
- No room details appear in the draft body or ai_context.
- No alternative-date language appears.
- No minimum spend appears.
- is_fallback=False and model="deterministic".
- The draft is persisted to the database.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch, call

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary
from app.modules.ai.service import DraftGenerationService
from app.modules.ai.schemas import DraftGenerationResult


# ── Shared fixtures ───────────────────────────────────────────────────────────


def _make_enquiry(enquiry_id: uuid.UUID) -> MagicMock:
    enquiry = MagicMock()
    enquiry.id = enquiry_id
    enquiry.restaurant_id = uuid.uuid4()
    enquiry.first_name = "Alice"
    enquiry.last_name = "Smith"
    enquiry.event_type = "corporate"
    enquiry.party_size = 20
    enquiry.event_date = None
    enquiry.notes = None
    enquiry.metadata_ = None
    enquiry.persona_id = None
    enquiry.preferred_area = None
    return enquiry


def _make_persona() -> MagicMock:
    persona = MagicMock()
    persona.name = "Events Team"
    persona.tone = "warm"
    persona.style = "concise"
    persona.system_prompt = "You are a warm hospitality professional."
    return persona


def _make_message(body: str) -> MagicMock:
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.subject = "Re: Corporate Enquiry — Alice Smith"
    msg.body = body
    return msg


def _build_service_with_mocks(enquiry_id: uuid.UUID):
    """Return (service, mock_db, mock_enquiry_repo) wired for a RESPOND_UNAVAILABLE plan."""
    db = MagicMock()
    svc = DraftGenerationService(db)

    enquiry = _make_enquiry(enquiry_id)
    persona = _make_persona()

    mock_enquiry_repo = MagicMock()
    mock_enquiry_repo.get_by_id.return_value = enquiry
    mock_enquiry_repo.get_latest_draft_message.return_value = None
    # add_message returns a mock message — body set after call
    def _add_message(eid, data):
        return _make_message(data["body"])
    mock_enquiry_repo.add_message.side_effect = _add_message

    mock_persona_repo = MagicMock()
    mock_persona_repo.get_by_id.return_value = None
    mock_persona_repo.get_default_persona_for_restaurant.return_value = persona

    mock_restaurant_repo = MagicMock()
    mock_restaurant = MagicMock()
    mock_restaurant.name = "The Grand"
    mock_restaurant.description = "A premier venue."
    mock_restaurant.address = "1 Grand Street"
    mock_restaurant_repo.get_by_id.return_value = mock_restaurant

    mock_room_repo = MagicMock()
    mock_room_repo.list_for_restaurant.return_value = []

    svc._enquiry_repo = mock_enquiry_repo
    svc._persona_repo = mock_persona_repo
    svc._restaurant_repo = mock_restaurant_repo
    svc._room_repo = mock_room_repo

    return svc, db, mock_enquiry_repo


def _make_unavailable_plan(
    *,
    availability_date: str = "2026-07-15",
    meal_period: str = "dinner",
) -> MagicMock:
    plan = MagicMock()
    plan.response_goal = "RESPOND_UNAVAILABLE"
    plan.clarification_questions = []
    plan.customer_type_context = {"final_customer_type": "corporate"}
    plan.section_plan = None
    plan.availability_context = {
        "availability_contract": "CONFIRMED_UNAVAILABLE",
        "restaurant_name": "The Grand",
        "room_name": "The Oak Room",
    }
    plan.date_context = {
        "status": "resolved",
        "date": availability_date,
        "meal_period": meal_period,
    }
    plan.known_facts = {}
    return plan


# ── Unit tests ────────────────────────────────────────────────────────────────


class TestDeterministicUnavailableDraft:
    def _run(self, enquiry_id: uuid.UUID, plan: MagicMock) -> DraftGenerationResult:
        svc, db, _ = _build_service_with_mocks(enquiry_id)
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = plan
            mock_plan_cls.return_value = mock_plan_repo
            result = svc.generate_draft(enquiry_id)
        return result

    def test_returns_draft_generation_result(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert isinstance(result, DraftGenerationResult)

    def test_model_is_deterministic(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.model == "deterministic"

    def test_is_fallback_false(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.is_fallback is False

    def test_body_contains_unavailable_opening(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan(availability_date="15th July", meal_period="dinner"))
        assert "fully booked" in result.body.lower()
        assert "unfortunately" in result.body.lower()

    def test_body_starts_with_dear_guest(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.body.startswith("Dear Alice,")

    def test_body_contains_signoff(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert "Warm regards" in result.body
        assert "Events Team" in result.body

    def test_body_contains_meal_period(self) -> None:
        """availability_meal_period comes from the processing snapshot, not the plan."""
        eid = uuid.uuid4()
        svc, db, _ = _build_service_with_mocks(eid)
        snapshot = MagicMock()
        snapshot.availability_result_json = {
            "status": "unavailable",
            "date": "2026-07-15",
            "meal_period": "lunch",
        }
        snapshot.pricing_result_json = None
        snapshot.room_suitability_json = None
        snapshot.missing_fields_json = None
        snapshot.recommended_action = None
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=snapshot),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = _make_unavailable_plan(meal_period="lunch")
            mock_plan_cls.return_value = mock_plan_repo
            result = svc.generate_draft(eid)
        assert "lunch" in result.body

    def test_body_contains_event_date(self) -> None:
        """availability_date comes from the processing snapshot, not the plan."""
        eid = uuid.uuid4()
        svc, db, _ = _build_service_with_mocks(eid)
        snapshot = MagicMock()
        snapshot.availability_result_json = {
            "status": "unavailable",
            "date": "2026-09-20",
            "meal_period": "dinner",
        }
        snapshot.pricing_result_json = None
        snapshot.room_suitability_json = None
        snapshot.missing_fields_json = None
        snapshot.recommended_action = None
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=snapshot),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = _make_unavailable_plan(availability_date="2026-09-20")
            mock_plan_cls.return_value = mock_plan_repo
            result = svc.generate_draft(eid)
        assert "2026-09-20" in result.body

    def test_enquiry_id_matches(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.enquiry_id == eid

    def test_ai_context_room_name_is_none(self) -> None:
        """No room details must appear in ai_context for unavailable responses."""
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.ai_context.room_name is None

    def test_no_alternative_date_language(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        body_lower = result.body.lower()
        forbidden = ["alternative date", "other date", "another date", "different date"]
        for phrase in forbidden:
            assert phrase not in body_lower, f"Found forbidden phrase: {phrase!r}"

    def test_no_room_suitability_language(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        body_lower = result.body.lower()
        forbidden = ["perfect for your", "ideal for your", "suitable for", "our room", "our space"]
        for phrase in forbidden:
            assert phrase not in body_lower, f"Found forbidden phrase: {phrase!r}"

    def test_no_minimum_spend_in_body(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert "minimum spend" not in result.body.lower()
        assert "£" not in result.body

    def test_no_future_availability_language(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        body_lower = result.body.lower()
        forbidden = ["check availability", "come back to you", "would love to host"]
        for phrase in forbidden:
            assert phrase not in body_lower, f"Found forbidden phrase: {phrase!r}"

    def test_ai_gateway_not_called(self) -> None:
        """LLM must never be invoked for RESPOND_UNAVAILABLE."""
        eid = uuid.uuid4()
        svc, db, _ = _build_service_with_mocks(eid)
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = _make_unavailable_plan()
            mock_plan_cls.return_value = mock_plan_repo
            svc.generate_draft(eid)

        mock_gw_cls.assert_not_called()

    def test_draft_persisted_to_db(self) -> None:
        """Draft message must be persisted as outbound/draft channel."""
        eid = uuid.uuid4()
        svc, db, mock_enquiry_repo = _build_service_with_mocks(eid)
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = _make_unavailable_plan()
            mock_plan_cls.return_value = mock_plan_repo
            svc.generate_draft(eid)

        mock_enquiry_repo.add_message.assert_called_once()
        call_kwargs = mock_enquiry_repo.add_message.call_args[0][1]
        assert call_kwargs["direction"] == "outbound"
        assert call_kwargs["channel"] == "draft"
        assert call_kwargs["sent_at"] is None

    def test_db_commit_called(self) -> None:
        eid = uuid.uuid4()
        svc, db, _ = _build_service_with_mocks(eid)
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = _make_unavailable_plan()
            mock_plan_cls.return_value = mock_plan_repo
            svc.generate_draft(eid)

        db.commit.assert_called()

    def test_subject_format(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert "Alice Smith" in result.subject
        assert "Enquiry" in result.subject

    def test_ai_context_model_is_deterministic(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.ai_context.model == "deterministic"

    def test_ai_context_is_fallback_false(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.ai_context.is_fallback is False

    def test_ai_context_system_prompt_is_none(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.ai_context.system_prompt is None

    def test_ai_context_prompt_run_id_is_none(self) -> None:
        eid = uuid.uuid4()
        result = self._run(eid, _make_unavailable_plan())
        assert result.ai_context.prompt_run_id is None


class TestDeterministicUnavailableFallbacks:
    """Edge cases when availability_date or meal_period is absent."""

    def _run_with_no_date_period(self, enquiry_id: uuid.UUID) -> DraftGenerationResult:
        plan = MagicMock()
        plan.response_goal = "RESPOND_UNAVAILABLE"
        plan.clarification_questions = []
        plan.customer_type_context = None
        plan.section_plan = None
        # No date or meal period in availability_context
        plan.availability_context = {"availability_contract": "CONFIRMED_UNAVAILABLE"}
        plan.date_context = {"status": "unknown"}
        plan.known_facts = {}

        svc, db, _ = _build_service_with_mocks(enquiry_id)
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = plan
            mock_plan_cls.return_value = mock_plan_repo
            return svc.generate_draft(enquiry_id)

    def test_body_uses_dinner_fallback_when_no_meal_period(self) -> None:
        eid = uuid.uuid4()
        result = self._run_with_no_date_period(eid)
        assert "dinner" in result.body.lower()

    def test_body_uses_requested_date_fallback_when_no_date(self) -> None:
        eid = uuid.uuid4()
        result = self._run_with_no_date_period(eid)
        assert "the requested date" in result.body.lower()

    def test_body_is_not_empty(self) -> None:
        eid = uuid.uuid4()
        result = self._run_with_no_date_period(eid)
        assert len(result.body.strip()) > 50

    def test_body_still_contains_signoff(self) -> None:
        eid = uuid.uuid4()
        result = self._run_with_no_date_period(eid)
        assert "Warm regards" in result.body


class TestNonUnavailableGoalsStillUseLLM:
    """Verify that ACKNOWLEDGE still routes through the LLM path.

    RESP-038: CONFIRM_AVAILABLE is now fully deterministic (no gateway call).
    """

    def test_confirm_available_does_not_call_gateway(self) -> None:
        # RESP-038: CONFIRM_AVAILABLE is fully deterministic — gateway must NOT be called
        eid = uuid.uuid4()
        svc, db, mock_enquiry_repo = _build_service_with_mocks(eid)

        plan = MagicMock()
        plan.response_goal = "CONFIRM_AVAILABLE"
        plan.clarification_questions = []
        plan.customer_type_context = None
        plan.section_plan = None
        plan.availability_context = {"availability_contract": "CONFIRMED_AVAILABLE"}
        plan.date_context = {"status": "resolved"}
        plan.known_facts = {}

        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
            patch(
                "app.modules.ai.service._generate_warmth_sentence",
                return_value=None,
            ),
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = plan
            mock_plan_cls.return_value = mock_plan_repo

            mock_gw_instance = MagicMock()
            mock_gw_cls.return_value = mock_gw_instance

            svc.generate_draft(eid)

        mock_gw_instance.run.assert_not_called()

    def test_acknowledge_and_check_uses_deterministic_path(self) -> None:
        # RESP-036: ACKNOWLEDGE_AND_CHECK_AVAILABILITY is now fully deterministic
        eid = uuid.uuid4()
        svc, db, mock_enquiry_repo = _build_service_with_mocks(eid)

        plan = MagicMock()
        plan.response_goal = "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"
        plan.clarification_questions = []
        plan.customer_type_context = None
        plan.section_plan = None
        plan.availability_context = {"availability_contract": "NOT_CHECKED"}
        plan.date_context = {"status": "resolved"}
        plan.known_facts = {}

        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = plan
            mock_plan_cls.return_value = mock_plan_repo

            mock_gw_instance = MagicMock()
            mock_gw_cls.return_value = mock_gw_instance

            result = svc.generate_draft(eid)

        # Gateway must NOT be called — response is deterministic
        mock_gw_instance.run.assert_not_called()
        assert result.model == "deterministic"
        assert "availability" in result.body.lower() or "check" in result.body.lower()
