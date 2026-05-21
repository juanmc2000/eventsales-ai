"""Tests for AI-002: room/PDR context in draft generation.

All tests are unit tests (no DB, no LLM API required).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.schemas import DraftContext
from app.modules.ai.provider import FallbackProvider, _format_room_line
from app.modules.ai.service import _match_room, DraftGenerationService


# ── DraftContext — new optional fields ────────────────────────────────────────


def _make_context(**overrides) -> DraftContext:
    """Build a DraftContext with sensible defaults."""
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Jane",
        guest_last_name="Doe",
        event_type="birthday",
        event_date="2026-12-25",
        party_size=20,
        guest_message=None,
        restaurant_name="The Garden Room",
        restaurant_description=None,
        persona_name="The Host",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="",
        recommended_minimum_spend=None,
    )
    defaults.update(overrides)
    return DraftContext(**defaults)


def test_draft_context_has_room_fields_as_none_by_default() -> None:
    ctx = _make_context()
    assert ctx.room_name is None
    assert ctx.room_seated_capacity is None
    assert ctx.room_layouts is None
    assert ctx.room_amenities is None
    assert ctx.room_booking_url is None
    assert ctx.room_is_private_dining is False
    assert ctx.restaurant_address is None


def test_draft_context_accepts_room_fields() -> None:
    ctx = _make_context(
        room_name="The Oak Room",
        room_seated_capacity=40,
        room_layouts=["theatre", "banquet"],
        room_amenities=["AV screen"],
        room_booking_url="https://events.example.com/enquire",
        room_is_private_dining=True,
    )
    assert ctx.room_name == "The Oak Room"
    assert ctx.room_seated_capacity == 40
    assert ctx.room_is_private_dining is True


# ── _format_room_line ─────────────────────────────────────────────────────────


def test_format_room_line_empty_when_no_room() -> None:
    ctx = _make_context()
    assert _format_room_line(ctx) == ""


def test_format_room_line_includes_room_name() -> None:
    ctx = _make_context(room_name="The Oak Room")
    line = _format_room_line(ctx)
    assert "The Oak Room" in line


def test_format_room_line_includes_capacity() -> None:
    ctx = _make_context(room_name="The Oak Room", room_seated_capacity=40)
    line = _format_room_line(ctx)
    assert "40" in line


def test_format_room_line_includes_booking_url() -> None:
    ctx = _make_context(
        room_name="The Oak Room",
        room_booking_url="https://events.example.com/enquire",
    )
    line = _format_room_line(ctx)
    assert "https://events.example.com/enquire" in line


# ── FallbackProvider with room context ────────────────────────────────────────


def test_fallback_includes_room_name_when_present() -> None:
    provider = FallbackProvider()
    ctx = _make_context(room_name="The Mayfair Suite")
    result = provider.generate(ctx)
    assert "The Mayfair Suite" in result


def test_fallback_works_without_room_context() -> None:
    """Fallback must produce a valid draft even when all room fields are None."""
    provider = FallbackProvider()
    ctx = _make_context()
    result = provider.generate(ctx)
    assert isinstance(result, str)
    assert len(result) > 50


def test_fallback_includes_capacity_when_room_present() -> None:
    provider = FallbackProvider()
    ctx = _make_context(room_name="The Oak Room", room_seated_capacity=60)
    result = provider.generate(ctx)
    assert "60" in result


# ── _match_room ───────────────────────────────────────────────────────────────


def _make_room(
    name: str = "Room A",
    min_capacity: int = 10,
    max_capacity: int = 50,
    seated_capacity: int = 50,
    display_order: int = 1,
) -> MagicMock:
    room = MagicMock()
    room.name = name
    room.min_capacity = min_capacity
    room.max_capacity = max_capacity
    room.seated_capacity = seated_capacity
    room.display_order = display_order
    return room


def test_match_room_returns_none_when_no_rooms() -> None:
    assert _match_room([], party_size=20, preferred_area=None) is None


def test_match_room_preferred_area_takes_priority() -> None:
    rooms = [
        _make_room("The Oak Room", min_capacity=10, max_capacity=50),
        _make_room("The Ballroom", min_capacity=100, max_capacity=300),
    ]
    result = _match_room(rooms, party_size=200, preferred_area="Oak")
    assert result.name == "The Oak Room"


def test_match_room_preferred_area_case_insensitive() -> None:
    rooms = [_make_room("The Oak Room")]
    result = _match_room(rooms, party_size=None, preferred_area="oak room")
    assert result.name == "The Oak Room"


def test_match_room_by_party_size_capacity() -> None:
    rooms = [
        _make_room("Small PDR", min_capacity=5, max_capacity=15),
        _make_room("Medium Room", min_capacity=16, max_capacity=40),
        _make_room("Large Ballroom", min_capacity=50, max_capacity=300),
    ]
    result = _match_room(rooms, party_size=25, preferred_area=None)
    assert result.name == "Medium Room"


def test_match_room_falls_back_to_first_when_no_capacity_match() -> None:
    rooms = [
        _make_room("Small PDR", min_capacity=5, max_capacity=15),
        _make_room("Medium Room", min_capacity=16, max_capacity=40),
    ]
    result = _match_room(rooms, party_size=300, preferred_area=None)
    assert result.name == "Small PDR"


def test_match_room_returns_first_when_no_party_size() -> None:
    rooms = [
        _make_room("First Room"),
        _make_room("Second Room"),
    ]
    result = _match_room(rooms, party_size=None, preferred_area=None)
    assert result.name == "First Room"


# ── DraftGenerationService — room context wired in ────────────────────────────


def test_generate_draft_includes_room_context() -> None:
    """Room context should be included in the generated draft when rooms exist."""
    from app.modules.ai.service import DraftGenerationService

    mock_db = MagicMock()
    service = DraftGenerationService(mock_db)

    enquiry_id = uuid.uuid4()
    mock_enquiry = MagicMock()
    mock_enquiry.id = enquiry_id
    mock_enquiry.restaurant_id = uuid.uuid4()
    mock_enquiry.persona_id = None
    mock_enquiry.first_name = "Alice"
    mock_enquiry.last_name = "Brown"
    mock_enquiry.event_type = "birthday"
    mock_enquiry.event_date = None
    mock_enquiry.party_size = 30
    mock_enquiry.notes = None
    mock_enquiry.metadata_ = {}
    mock_enquiry.preferred_area = None

    mock_restaurant = MagicMock()
    mock_restaurant.name = "The Grand Hall"
    mock_restaurant.description = None
    mock_restaurant.address = "1 Grand Place, London"

    mock_room = MagicMock()
    mock_room.name = "The Crystal Suite"
    mock_room.room_type = "private_dining"
    mock_room.seated_capacity = 40
    mock_room.standing_capacity = 60
    mock_room.min_capacity = 10
    mock_room.max_capacity = 60
    mock_room.layouts = ["theatre", "banquet"]
    mock_room.amenities = ["AV screen"]
    mock_room.suitability_notes = "Perfect for celebrations."
    mock_room.booking_url = "https://events.example.com/enquire"
    mock_room.is_private_dining = True

    mock_message = MagicMock()
    mock_message.id = uuid.uuid4()

    service._enquiry_repo.get_by_id = MagicMock(return_value=mock_enquiry)
    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_by_id = MagicMock(return_value=None)
    service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
    service._room_repo.list_for_restaurant = MagicMock(return_value=[mock_room])
    service._enquiry_repo.add_message = MagicMock(return_value=mock_message)

    with patch("app.modules.ai.service.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        result = service.generate_draft(enquiry_id)

    assert "The Crystal Suite" in result.body
    assert result.is_fallback is True


def test_generate_draft_works_without_rooms() -> None:
    """Draft generation must not fail when no rooms exist."""
    from app.modules.ai.service import DraftGenerationService

    mock_db = MagicMock()
    service = DraftGenerationService(mock_db)

    enquiry_id = uuid.uuid4()
    mock_enquiry = MagicMock()
    mock_enquiry.id = enquiry_id
    mock_enquiry.restaurant_id = uuid.uuid4()
    mock_enquiry.persona_id = None
    mock_enquiry.first_name = "Bob"
    mock_enquiry.last_name = "Smith"
    mock_enquiry.event_type = "corporate"
    mock_enquiry.event_date = None
    mock_enquiry.party_size = 20
    mock_enquiry.notes = None
    mock_enquiry.metadata_ = {}
    mock_enquiry.preferred_area = None

    mock_restaurant = MagicMock()
    mock_restaurant.name = "City Brasserie"
    mock_restaurant.description = None
    mock_restaurant.address = None

    mock_message = MagicMock()
    mock_message.id = uuid.uuid4()

    service._enquiry_repo.get_by_id = MagicMock(return_value=mock_enquiry)
    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_by_id = MagicMock(return_value=None)
    service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
    service._room_repo.list_for_restaurant = MagicMock(return_value=[])
    service._enquiry_repo.add_message = MagicMock(return_value=mock_message)

    with patch("app.modules.ai.service.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        result = service.generate_draft(enquiry_id)

    assert result.body != ""
    assert result.is_fallback is True
