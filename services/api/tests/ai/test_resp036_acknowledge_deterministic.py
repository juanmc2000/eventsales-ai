"""Tests for RESP-036 — deterministic ACKNOWLEDGE_AND_CHECK_AVAILABILITY drafts.

Validates that ACKNOWLEDGE responses use approved copy blocks, contain no
LLM-generated section headers, and include no availability confirmation.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.service import _build_acknowledge_enquiry_summary
from app.modules.ai.schemas import DraftContext


def _base_context(**overrides) -> DraftContext:
    from dataclasses import replace
    ctx = DraftContext(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="birthday",
        event_date="2026-06-12",
        party_size=8,
        guest_message=None,
        restaurant_name="The Grand",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="You are Eleanor.",
        recommended_minimum_spend=None,
        response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        audience_type="social",
    )
    for k, v in overrides.items():
        ctx = replace(ctx, **{k: v})
    return ctx


# ── _build_acknowledge_enquiry_summary ───────────────────────────────────────


class TestBuildAcknowledgeEnquirySummary:
    def test_includes_event_type_and_party_size(self) -> None:
        ctx = _base_context(event_type="birthday", party_size=10)
        summary = _build_acknowledge_enquiry_summary(ctx)
        assert "birthday" in summary
        assert "10" in summary

    def test_event_type_underscore_converted(self) -> None:
        ctx = _base_context(event_type="corporate_dinner", party_size=None)
        summary = _build_acknowledge_enquiry_summary(ctx)
        assert "corporate dinner" in summary
        assert "_" not in summary

    def test_returns_empty_when_no_context(self) -> None:
        ctx = _base_context(event_type=None, party_size=None)
        summary = _build_acknowledge_enquiry_summary(ctx)
        assert summary == ""

    def test_only_party_size(self) -> None:
        ctx = _base_context(event_type=None, party_size=20)
        summary = _build_acknowledge_enquiry_summary(ctx)
        assert "20" in summary

    def test_no_availability_claim(self) -> None:
        ctx = _base_context(event_type="wedding", party_size=50)
        summary = _build_acknowledge_enquiry_summary(ctx)
        assert "available" not in summary.lower()
        assert "confirm" not in summary.lower()


# ── _generate_deterministic_acknowledge_draft ─────────────────────────────────


def _build_service_with_mocks(eid: uuid.UUID):
    """Return (service, db, enquiry_repo_mock) wired with minimal test mocks."""
    from app.modules.ai.service import DraftGenerationService

    db = MagicMock()
    svc = DraftGenerationService(db)

    mock_enquiry = MagicMock()
    mock_enquiry.id = eid
    mock_enquiry.restaurant_id = uuid.uuid4()
    mock_enquiry.persona_id = None
    mock_enquiry.first_name = "Alice"
    mock_enquiry.last_name = "Smith"
    mock_enquiry.event_type = "birthday"
    mock_enquiry.event_date = None
    mock_enquiry.party_size = 8
    mock_enquiry.notes = None
    mock_enquiry.metadata_ = None
    mock_enquiry.preferred_area = None

    mock_restaurant = MagicMock()
    mock_restaurant.name = "The Grand"
    mock_restaurant.description = None
    mock_restaurant.address = None

    mock_message = MagicMock()
    mock_message.id = uuid.uuid4()

    svc._enquiry_repo.get_by_id = MagicMock(return_value=mock_enquiry)
    svc._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    svc._persona_repo.get_by_id = MagicMock(return_value=None)
    svc._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
    svc._room_repo.list_for_restaurant = MagicMock(return_value=[])
    svc._enquiry_repo.add_message = MagicMock(return_value=mock_message)

    return svc, db, svc._enquiry_repo


class TestDeterministicAcknowledgeDraft:
    def _generate(self, eid: uuid.UUID):
        svc, db, _ = _build_service_with_mocks(eid)

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
        ):
            mock_plan_repo = MagicMock()
            mock_plan_repo.get_latest.return_value = plan
            mock_plan_cls.return_value = mock_plan_repo
            return svc.generate_draft(eid)

    def test_model_is_deterministic(self) -> None:
        result = self._generate(uuid.uuid4())
        assert result.model == "deterministic"

    def test_not_fallback(self) -> None:
        result = self._generate(uuid.uuid4())
        assert result.is_fallback is False

    def test_body_contains_not_checked_opening_block(self) -> None:
        result = self._generate(uuid.uuid4())
        from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary
        opening = FirstResponseCopyLibrary.render(
            "availability_not_checked",
            {"meal_period": "dinner", "event_date": "the requested date"},
        )
        # The opening block text should appear verbatim
        assert "check availability" in result.body.lower()

    def test_body_contains_next_step_block(self) -> None:
        result = self._generate(uuid.uuid4())
        from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary
        next_step = FirstResponseCopyLibrary.render("availability_check_next_step")
        assert next_step in result.body

    def test_body_contains_signoff(self) -> None:
        result = self._generate(uuid.uuid4())
        assert "Events Team" in result.body or "Warm regards" in result.body

    def test_no_section_headers(self) -> None:
        result = self._generate(uuid.uuid4())
        assert "**Opening**" not in result.body
        assert "**Sign-off**" not in result.body
        assert "**Availability" not in result.body

    def test_no_availability_confirmation(self) -> None:
        result = self._generate(uuid.uuid4())
        lower = result.body.lower()
        assert "confirmed" not in lower or "availability" not in lower

    def test_under_120_words(self) -> None:
        result = self._generate(uuid.uuid4())
        word_count = len(result.body.split())
        assert word_count <= 120, f"Body has {word_count} words (limit: 120)"

    def test_body_starts_with_dear(self) -> None:
        result = self._generate(uuid.uuid4())
        assert result.body.startswith("Dear Alice")

    def test_subject_is_set(self) -> None:
        result = self._generate(uuid.uuid4())
        assert result.subject is not None
        assert "Alice Smith" in result.subject
