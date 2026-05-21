"""
TEST-004: Sprint 4 Draft Response Fallback Tests.

Verifies that the FallbackProvider generates a well-formed deterministic
draft response without any API call, and that make_provider() selects
the fallback when no API key is present.
"""

from __future__ import annotations

import uuid

from app.modules.ai.provider import DraftContext, FallbackProvider, make_provider


def _context(**overrides) -> DraftContext:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="Birthday",
        event_date="2026-07-01",
        party_size=10,
        guest_message="Looking forward to the event.",
        restaurant_name="The Grand",
        restaurant_description="Upscale dining in the city centre.",
        persona_name="The Host",
        persona_tone="warm",
        persona_style="professional",
        persona_system_prompt="You are a warm, professional event host.",
        recommended_minimum_spend=1500.0,
    )
    defaults.update(overrides)
    return DraftContext(**defaults)


class TestFallbackProvider:
    def test_generate_returns_string(self):
        result = FallbackProvider().generate(_context())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_addresses_guest_by_first_name(self):
        result = FallbackProvider().generate(_context(guest_first_name="Alice"))
        assert "Alice" in result

    def test_generate_mentions_restaurant_name(self):
        result = FallbackProvider().generate(_context(restaurant_name="The Grand"))
        assert "The Grand" in result

    def test_generate_mentions_persona_name(self):
        result = FallbackProvider().generate(_context(persona_name="The Host"))
        assert "The Host" in result

    def test_generate_includes_spend_when_set(self):
        result = FallbackProvider().generate(_context(recommended_minimum_spend=1500.0))
        assert "1,500" in result or "1500" in result

    def test_generate_omits_spend_when_none(self):
        result = FallbackProvider().generate(_context(recommended_minimum_spend=None))
        assert "minimum spend" not in result.lower()

    def test_generate_mentions_event_type(self):
        result = FallbackProvider().generate(_context(event_type="Birthday"))
        assert "Birthday" in result

    def test_generate_is_deterministic(self):
        ctx = _context()
        assert FallbackProvider().generate(ctx) == FallbackProvider().generate(ctx)

    def test_generate_no_party_size_still_works(self):
        result = FallbackProvider().generate(_context(party_size=None))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_model_name(self):
        assert FallbackProvider().model_name == "fallback-template-v1"


class TestMakeProvider:
    def test_returns_fallback_when_no_api_key(self):
        provider, is_fallback = make_provider("")
        assert is_fallback is True
        assert isinstance(provider, FallbackProvider)

    def test_fallback_provider_generates_without_api_key(self):
        provider, is_fallback = make_provider("")
        result = provider.generate(_context())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_generates_dear_greeting(self):
        provider, _ = make_provider("")
        result = provider.generate(_context(guest_first_name="Bob"))
        assert "Dear Bob" in result
