"""Tests for RESP-021 — Context Integrity Gate wired into DraftGenerationService.

Validates:
- Restaurant name mismatch in snapshot blocks LLM gateway call → is_fallback=True
- Room name mismatch in snapshot blocks LLM gateway call → is_fallback=True
- Matching context allows normal LLM gateway call
- Absent availability identifiers in snapshot allows normal LLM gateway call
- Integrity failure is visible via is_fallback=True in returned result
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    RUN_STATUS_FALLBACK,
    RUN_STATUS_SUCCESS,
    VALIDATION_SKIPPED,
)
from app.modules.ai.schemas import AIGatewayResult


def _make_gateway_result(
    is_fallback: bool = False,
    raw_response: str | None = "Dear Alice, thank you.",
    model_name: str = "claude-haiku-4-5-20251001",
    run_id: uuid.UUID | None = None,
) -> AIGatewayResult:
    return AIGatewayResult(
        run_id=run_id or uuid.uuid4(),
        prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
        prompt_version=6,
        model_name="fallback" if is_fallback else model_name,
        model_provider="fallback" if is_fallback else "anthropic",
        rendered_system_prompt=None if is_fallback else "System prompt",
        rendered_user_prompt=None if is_fallback else "User prompt",
        raw_response=None if is_fallback else raw_response,
        is_fallback=is_fallback,
        fallback_reason="no_api_key" if is_fallback else None,
        validation_status=VALIDATION_SKIPPED,
        latency_ms=0 if is_fallback else 100,
        status=RUN_STATUS_FALLBACK if is_fallback else RUN_STATUS_SUCCESS,
    )


def _make_enquiry(enquiry_id: uuid.UUID | None = None) -> MagicMock:
    enquiry = MagicMock()
    enquiry.id = enquiry_id or uuid.uuid4()
    enquiry.restaurant_id = uuid.uuid4()
    enquiry.persona_id = uuid.uuid4()
    enquiry.first_name = "Alice"
    enquiry.last_name = "Smith"
    enquiry.event_type = "birthday"
    enquiry.event_date = None
    enquiry.party_size = 8
    enquiry.notes = "Lovely birthday dinner."
    enquiry.metadata_ = {}
    return enquiry


def _make_persona() -> MagicMock:
    persona = MagicMock()
    persona.name = "Eleanor"
    persona.tone = "warm"
    persona.style = "concise"
    persona.system_prompt = "You are Eleanor."
    return persona


def _make_restaurant(name: str = "The Ivy Tower Bridge") -> MagicMock:
    r = MagicMock()
    r.name = name
    r.description = None
    r.address = None
    return r


def _make_message() -> MagicMock:
    msg = MagicMock()
    msg.id = uuid.uuid4()
    return msg


def _make_snapshot(
    restaurant_name: str | None = None,
    room_name: str | None = None,
) -> MagicMock:
    """Build a processing snapshot with optional availability restaurant/room names."""
    snap = MagicMock()
    avail_json: dict = {"status": "available", "date": "2026-06-20", "meal_period": "dinner"}
    if restaurant_name is not None:
        avail_json["restaurant_name"] = restaurant_name
    if room_name is not None:
        avail_json["room_name"] = room_name
    snap.availability_result_json = avail_json
    snap.pricing_result_json = None
    snap.room_suitability_json = None
    snap.missing_fields_json = None
    snap.recommended_action = None
    return snap


# ── Mismatch blocks LLM ───────────────────────────────────────────────────────


class TestIntegrityGateBlocksLlm:
    def _run_generate(self, snapshot_restaurant: str) -> object:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_restaurant("The Ivy Tower Bridge"))
        service._persona_repo.get_by_id = MagicMock(return_value=_make_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_message())

        snapshot = _make_snapshot(restaurant_name=snapshot_restaurant)

        with (
            patch(
                "app.modules.ai.service._load_latest_processing_snapshot",
                return_value=snapshot,
            ),
            patch(
                "app.modules.ai.service._enrich_context_from_snapshot",
                side_effect=lambda ctx, snap: ctx,
            ),
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result()
            mock_gw_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)

            return result, mock_gw

    def test_restaurant_name_mismatch_sets_is_fallback(self) -> None:
        result, mock_gw = self._run_generate(snapshot_restaurant="The Grand Ballroom")
        assert result.is_fallback is True

    def test_restaurant_name_mismatch_does_not_call_gateway(self) -> None:
        result, mock_gw = self._run_generate(snapshot_restaurant="The Grand Ballroom")
        mock_gw.run.assert_not_called()

    def test_restaurant_name_match_calls_gateway(self) -> None:
        result, mock_gw = self._run_generate(snapshot_restaurant="The Ivy Tower Bridge")
        mock_gw.run.assert_called_once()

    def test_no_availability_name_calls_gateway(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_message())

        snapshot = _make_snapshot()  # no restaurant_name in avail_json

        with (
            patch(
                "app.modules.ai.service._load_latest_processing_snapshot",
                return_value=snapshot,
            ),
            patch(
                "app.modules.ai.service._enrich_context_from_snapshot",
                side_effect=lambda ctx, snap: ctx,
            ),
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result()
            mock_gw_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)
            mock_gw.run.assert_called_once()

    def test_no_snapshot_calls_gateway(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_message())

        with (
            patch(
                "app.modules.ai.service._load_latest_processing_snapshot",
                return_value=None,
            ),
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result()
            mock_gw_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)
            mock_gw.run.assert_called_once()


# ── Room mismatch ─────────────────────────────────────────────────────────────


class TestRoomMismatchBlocksLlm:
    def _run_with_room(self, context_room: str, avail_room: str) -> tuple:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_message())

        snapshot = _make_snapshot(room_name=avail_room)

        from app.modules.ai.schemas import DraftContext
        from dataclasses import replace

        def enrich_with_room(ctx, snap):
            return replace(ctx, room_name=context_room)

        with (
            patch(
                "app.modules.ai.service._load_latest_processing_snapshot",
                return_value=snapshot,
            ),
            patch(
                "app.modules.ai.service._enrich_context_from_snapshot",
                side_effect=enrich_with_room,
            ),
            patch("app.modules.ai.service.AIGateway") as mock_gw_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result()
            mock_gw_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)
            return result, mock_gw

    def test_room_name_mismatch_sets_is_fallback(self) -> None:
        result, _ = self._run_with_room("Private Dining Room", "The Mayfair Suite")
        assert result.is_fallback is True

    def test_room_name_mismatch_does_not_call_gateway(self) -> None:
        result, mock_gw = self._run_with_room("Private Dining Room", "The Mayfair Suite")
        mock_gw.run.assert_not_called()

    def test_room_name_match_calls_gateway(self) -> None:
        result, mock_gw = self._run_with_room("Private Dining Room", "Private Dining Room")
        mock_gw.run.assert_called_once()
