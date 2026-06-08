"""Tests for RESP-028 — Deterministic RESPOND_UNAVAILABLE routing in production and tests.

Verifies that:
- RESPOND_UNAVAILABLE returns a DraftGenerationResult with review_state set
- review_state.status is HUMAN_REVIEW_REQUIRED (goal not in auto-send allowlist)
- review_state.auto_send_allowed is False
- review_state.validation_passed is True (deterministic copy always compliant)
- model field is "deterministic" — no LLM provider called
- ai_context.prompt_run_id is None — no prompt run created
- ai_context.system_prompt is None — no prompt rendered
- CONFIRM_AVAILABLE and other goals still return review_state (LLM path)
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.modules.ai.service import DraftGenerationService
from app.modules.ai.schemas import DraftGenerationResult
from app.modules.ai.draft_review_state import HUMAN_REVIEW_REQUIRED, AUTO_SEND_ELIGIBLE


# ── Shared helpers ─────────────────────────────────────────────────────────────


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


def _build_service(enquiry_id: uuid.UUID):
    """Return (service, db, mock_enquiry_repo) with all repos mocked."""
    db = MagicMock()
    svc = DraftGenerationService(db)

    enquiry = _make_enquiry(enquiry_id)
    persona = _make_persona()

    mock_enquiry_repo = MagicMock()
    mock_enquiry_repo.get_by_id.return_value = enquiry

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


def _make_plan(response_goal: str) -> MagicMock:
    plan = MagicMock()
    plan.response_goal = response_goal
    plan.clarification_questions = []
    plan.customer_type_context = {"final_customer_type": "corporate"}
    plan.section_plan = None
    plan.availability_context = {
        "availability_contract": (
            "CONFIRMED_UNAVAILABLE" if response_goal == "RESPOND_UNAVAILABLE"
            else "CONFIRMED_AVAILABLE"
        ),
    }
    plan.date_context = {"status": "resolved"}
    plan.known_facts = {}
    return plan


def _run_with_goal(response_goal: str) -> DraftGenerationResult:
    eid = uuid.uuid4()
    svc, db, _ = _build_service(eid)
    plan = _make_plan(response_goal)

    if response_goal == "RESPOND_UNAVAILABLE":
        with (
            patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
            patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = plan
            mock_plan_cls.return_value = mock_plan_repo
            return svc.generate_draft(eid)

    mock_gw_result = MagicMock()
    mock_gw_result.is_fallback = False
    mock_gw_result.model_name = "claude-haiku-4-5-20251001"
    mock_gw_result.raw_response = "Dear Alice, we are pleased to confirm availability."
    mock_gw_result.rendered_system_prompt = None
    mock_gw_result.rendered_user_prompt = None
    mock_gw_result.run_id = uuid.uuid4()

    with (
        patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None),
        patch("app.modules.enquiries.repository.ResponsePlanRepository") as mock_plan_cls,
        patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
    ):
        mock_plan_repo = MagicMock()
        mock_plan_repo.get_latest.return_value = plan
        mock_plan_cls.return_value = mock_plan_repo
        mock_gw_instance = MagicMock()
        mock_gw_instance.run.return_value = mock_gw_result
        mock_gw_cls.return_value = mock_gw_instance
        return svc.generate_draft(eid)


# ── RESP-028: Review state for deterministic RESPOND_UNAVAILABLE ───────────────


class TestDeterministicUnavailableReviewState:
    """RESP-028: review_state must be set on the deterministic path."""

    def test_review_state_is_set(self) -> None:
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.review_state is not None

    def test_review_state_status_is_human_review_required(self) -> None:
        """RESPOND_UNAVAILABLE is not in the auto-send allowlist."""
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.review_state.status == HUMAN_REVIEW_REQUIRED

    def test_review_state_auto_send_allowed_false(self) -> None:
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.review_state.auto_send_allowed is False

    def test_review_state_validation_passed_true(self) -> None:
        """Deterministic copy always passes compliance — no LLM hallucinations possible."""
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.review_state.validation_passed is True

    def test_review_state_no_validation_violations(self) -> None:
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.review_state.validation_violations == []


# ── RESP-028: Generation path markers ────────────────────────────────────────


class TestDeterministicPathMarkers:
    """Verify that RESPOND_UNAVAILABLE is clearly identified as deterministic."""

    def test_model_is_deterministic(self) -> None:
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.model == "deterministic"

    def test_is_fallback_false(self) -> None:
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.is_fallback is False

    def test_ai_context_prompt_run_id_is_none(self) -> None:
        """No prompt run is created for deterministic drafts."""
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.ai_context.prompt_run_id is None

    def test_ai_context_system_prompt_is_none(self) -> None:
        """No prompt is rendered for deterministic drafts."""
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.ai_context.system_prompt is None

    def test_ai_context_model_is_deterministic(self) -> None:
        result = _run_with_goal("RESPOND_UNAVAILABLE")
        assert result.ai_context.model == "deterministic"


# ── RESP-028: Non-unavailable goals still route to LLM ───────────────────────


class TestLlmGoalsReturnReviewState:
    """LLM-generated drafts also return review_state (AUTO-002 path)."""

    def test_confirm_available_review_state_is_set(self) -> None:
        result = _run_with_goal("CONFIRM_AVAILABLE")
        assert result.review_state is not None

    def test_confirm_available_model_is_not_deterministic(self) -> None:
        result = _run_with_goal("CONFIRM_AVAILABLE")
        assert result.model != "deterministic"
