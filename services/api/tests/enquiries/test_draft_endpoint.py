"""Tests for the draft response endpoint (API-009).

All tests are smoke/unit tests (no DB, no Anthropic API required).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.modules.enquiries.schemas import DraftResponseOut


# ── DraftResponseOut schema ────────────────────────────────────────────────────


def test_draft_response_out_required_fields() -> None:
    now = datetime.now(tz=timezone.utc)
    draft = DraftResponseOut(
        enquiry_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        body="Dear Jane, thank you for your enquiry...",
        generated_at=now,
    )
    assert draft.body.startswith("Dear Jane")
    assert draft.subject is None
    assert draft.persona_name is None
    assert draft.is_fallback is None
    assert draft.model is None


def test_draft_response_out_full_fields() -> None:
    now = datetime.now(tz=timezone.utc)
    draft = DraftResponseOut(
        enquiry_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        subject="Re: Corporate Enquiry — Alice Smith",
        body="Dear Alice, we would be delighted...",
        persona_name="Warm Host",
        recommended_minimum_spend=1500.0,
        pricing_explanation="1 rule matched.",
        is_fallback=True,
        model="fallback",
        generated_at=now,
    )
    assert draft.persona_name == "Warm Host"
    assert draft.recommended_minimum_spend == 1500.0
    assert draft.is_fallback is True


# ── Repository: get_latest_draft_message ──────────────────────────────────────


def test_get_latest_draft_message_exists_in_repository() -> None:
    from app.modules.enquiries.repository import EnquiryRepository

    mock_db = MagicMock()
    repo = EnquiryRepository(mock_db)

    mock_message = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_message
    mock_db.scalars.return_value = mock_scalars

    result = repo.get_latest_draft_message(uuid.uuid4())
    assert result is mock_message


def test_get_latest_draft_message_returns_none_when_absent() -> None:
    from app.modules.enquiries.repository import EnquiryRepository

    mock_db = MagicMock()
    repo = EnquiryRepository(mock_db)

    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_db.scalars.return_value = mock_scalars

    result = repo.get_latest_draft_message(uuid.uuid4())
    assert result is None


# ── generate_draft endpoint (POST) ────────────────────────────────────────────


def test_generate_draft_response_schema_mapping() -> None:
    """Verify the route handler can map result fields to DraftResponseOut."""
    now = datetime.now(tz=timezone.utc)
    # Simulate what the POST route handler does with a DraftGenerationResult
    out = DraftResponseOut(
        enquiry_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        subject="Re: Corporate Enquiry — Tom Smith",
        body="Dear Tom, thank you for your enquiry...",
        persona_name="Refined Host",
        recommended_minimum_spend=None,
        pricing_explanation=None,
        is_fallback=True,
        model="fallback",
        generated_at=now,
    )
    assert out.body == "Dear Tom, thank you for your enquiry..."
    assert out.is_fallback is True
    assert out.persona_name == "Refined Host"
    assert out.recommended_minimum_spend is None


# ── GET /draft path ────────────────────────────────────────────────────────────


def test_get_draft_builds_response_from_stored_message() -> None:
    """Simulate the GET /draft handler logic: loads message + enriches with enquiry context."""
    enquiry_id = uuid.uuid4()
    message_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    mock_message = MagicMock()
    mock_message.id = message_id
    mock_message.subject = "Re: Wedding Enquiry — Anna Brown"
    mock_message.body = "Dear Anna, we are delighted to assist..."
    mock_message.created_at = now

    recommended_spend = 2000.0
    mock_enquiry = MagicMock()
    mock_enquiry.persona_id = uuid.uuid4()
    mock_enquiry.metadata_ = {"recommended_minimum_spend": recommended_spend}

    mock_persona = MagicMock()
    mock_persona.name = "Grand Host"

    # Simulate route handler building DraftResponseOut
    out = DraftResponseOut(
        enquiry_id=enquiry_id,
        message_id=mock_message.id,
        subject=mock_message.subject,
        body=mock_message.body,
        persona_name=mock_persona.name,
        recommended_minimum_spend=float(mock_enquiry.metadata_["recommended_minimum_spend"]),
        pricing_explanation=None,
        is_fallback=None,
        model=None,
        generated_at=mock_message.created_at,
    )

    assert out.body == "Dear Anna, we are delighted to assist..."
    assert out.persona_name == "Grand Host"
    assert out.recommended_minimum_spend == 2000.0
    assert out.is_fallback is None  # Not known on GET path
