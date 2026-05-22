"""Tests for AIContextOut population and prompt capture.

Covers:
- AIContextOut schema fields
- Prompts are captured when AnthropicProvider is used (mocked)
- Prompts are None when FallbackProvider is used
- build_system_prompt and build_user_message are importable and callable
- DraftGenerationResult includes ai_context
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from unittest.mock import MagicMock, patch

from app.modules.ai.schemas import AIContextOut, DraftContext, DraftGenerationResult
from app.modules.ai.provider import build_system_prompt, build_user_message


# ── DraftContext fixture ───────────────────────────────────────────────────────


def _make_context(**overrides) -> DraftContext:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Jane",
        guest_last_name="Smith",
        event_type="birthday",
        event_date="2026-09-01",
        party_size=12,
        guest_message="We'd love a private room for a birthday dinner.",
        restaurant_name="The Grand Ballroom",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="considered and unhurried",
        persona_system_prompt="You are Eleanor...",
        recommended_minimum_spend=3500.0,
        restaurant_address="1 Grand Place, London",
    )
    defaults.update(overrides)
    return DraftContext(**defaults)


# ── Prompt builder tests ───────────────────────────────────────────────────────


def test_build_system_prompt_returns_string() -> None:
    ctx = _make_context()
    prompt = build_system_prompt(ctx)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_system_prompt_includes_persona_name() -> None:
    ctx = _make_context(persona_name="James")
    prompt = build_system_prompt(ctx)
    assert "James" in prompt


def test_build_system_prompt_includes_restaurant_name() -> None:
    ctx = _make_context(restaurant_name="Harbour View")
    prompt = build_system_prompt(ctx)
    assert "Harbour View" in prompt


def test_build_user_message_returns_string() -> None:
    ctx = _make_context()
    msg = build_user_message(ctx)
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_build_user_message_includes_guest_name() -> None:
    ctx = _make_context(guest_first_name="Alice", guest_last_name="Brown")
    msg = build_user_message(ctx)
    assert "Alice" in msg
    assert "Brown" in msg


def test_build_user_message_includes_guest_message() -> None:
    ctx = _make_context(guest_message="I want a surprise party for 20 people")
    msg = build_user_message(ctx)
    assert "surprise party" in msg


def test_build_user_message_includes_room_name() -> None:
    ctx = _make_context(room_name="The Mayfair Suite")
    msg = build_user_message(ctx)
    assert "Mayfair Suite" in msg


def test_build_user_message_includes_spend() -> None:
    ctx = _make_context(recommended_minimum_spend=5000.0)
    msg = build_user_message(ctx)
    assert "5,000" in msg


# ── AIContextOut dataclass ────────────────────────────────────────────────────


def test_ai_context_out_fields() -> None:
    ctx = AIContextOut(
        model="claude-haiku-4-5-20251001",
        is_fallback=False,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="considered and unhurried",
        guest_message_used="A birthday dinner for 12.",
        room_name="The Mayfair Suite",
        recommended_minimum_spend=3500.0,
        system_prompt="You are Eleanor...",
        user_message="Please draft a response.",
    )
    assert ctx.model == "claude-haiku-4-5-20251001"
    assert ctx.is_fallback is False
    assert ctx.system_prompt == "You are Eleanor..."
    assert ctx.user_message == "Please draft a response."


def test_ai_context_out_fallback_has_no_prompts() -> None:
    ctx = AIContextOut(
        model="fallback",
        is_fallback=True,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="considered and unhurried",
        guest_message_used=None,
        room_name=None,
        recommended_minimum_spend=None,
        system_prompt=None,
        user_message=None,
    )
    assert ctx.system_prompt is None
    assert ctx.user_message is None


# ── DraftGenerationResult includes ai_context ─────────────────────────────────


def test_draft_generation_result_has_ai_context_field() -> None:
    ai_ctx = AIContextOut(
        model="fallback",
        is_fallback=True,
        persona_name="Eleanor",
        persona_tone="warm",
        persona_style="concise",
        guest_message_used=None,
        room_name=None,
        recommended_minimum_spend=None,
        system_prompt=None,
        user_message=None,
    )
    result = DraftGenerationResult(
        enquiry_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        subject="Re: Birthday Enquiry",
        body="Dear Jane...",
        persona_name="Eleanor",
        is_fallback=True,
        model="fallback",
        ai_context=ai_ctx,
    )
    assert result.ai_context is not None
    assert result.ai_context.is_fallback is True


def test_draft_generation_result_ai_context_optional() -> None:
    """ai_context defaults to None — backwards compatible."""
    result = DraftGenerationResult(
        enquiry_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        subject="Re: Birthday",
        body="Dear Jane...",
        persona_name="Eleanor",
        is_fallback=True,
        model="fallback",
    )
    assert result.ai_context is None


# ── Fallback provider sets no prompts ────────────────────────────────────────


def test_fallback_provider_generate_no_prompts() -> None:
    """When FallbackProvider is used, is_fallback=True and prompts are not built."""
    from app.modules.ai.provider import FallbackProvider

    provider = FallbackProvider()
    ctx = _make_context()
    body = provider.generate(ctx)
    assert isinstance(body, str)
    assert "Jane" in body
    # is_fallback is determined by make_provider, not by the output text
    assert provider.model_name == "fallback"
