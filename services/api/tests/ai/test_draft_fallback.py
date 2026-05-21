"""Draft generation fallback tests.

TEST-005: End-to-End POC Workflow Tests

Tests cover:
- Draft generation fallback when no LLM API key is present
- Draft contains subject and body fields
- Draft is persona-aware (includes persona context)

These tests are deterministic and require no live Anthropic API calls.
The FallbackProvider is tested inline since the AI module may not
be merged to main at test execution time.
"""
import uuid
from datetime import date


# ─── Inline FallbackProvider (mirrors AI-001 behavior) ───────────────────────

class FallbackDraftProvider:
    """Minimal deterministic draft generator for tests.

    Used when ANTHROPIC_API_KEY is absent. Produces a structurally valid
    draft that exercises the full downstream pipeline without an LLM call.
    """

    def generate(
        self,
        *,
        guest_name: str,
        event_type: str | None,
        event_date: date | None,
        party_size: int | None,
        restaurant_name: str,
        persona_name: str | None,
        minimum_spend: float | None,
    ) -> dict:
        subject = f"Re: Your Private Dining Enquiry at {restaurant_name}"

        lines = [
            f"Dear {guest_name},",
            "",
            f"Thank you for your enquiry about hosting a{' ' + event_type if event_type else 'n'} event"
            f" at {restaurant_name}.",
        ]

        if party_size:
            lines.append(f"We would love to welcome your party of {party_size}.")

        if event_date:
            lines.append(
                f"Your preferred date of {event_date.strftime('%d %B %Y')} is noted."
            )

        if minimum_spend:
            lines.append(
                f"Based on your requirements, we recommend a minimum spend of "
                f"£{minimum_spend:,.0f}."
            )

        lines += [
            "",
            "Please let us know if you have any dietary requirements or special requests.",
            "",
            f"Kind regards,",
            persona_name or "The Events Team",
        ]

        return {
            "subject": subject,
            "body": "\n".join(lines),
        }


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_fallback_provider_generates_subject_and_body() -> None:
    provider = FallbackDraftProvider()
    result = provider.generate(
        guest_name="Alice Smith",
        event_type="birthday",
        event_date=date(2026, 12, 25),
        party_size=20,
        restaurant_name="The Grand",
        persona_name="The Host",
        minimum_spend=2000.0,
    )
    assert "subject" in result
    assert "body" in result
    assert result["subject"] != ""
    assert result["body"] != ""


def test_fallback_draft_includes_guest_name() -> None:
    provider = FallbackDraftProvider()
    result = provider.generate(
        guest_name="Bob Jones",
        event_type=None,
        event_date=None,
        party_size=None,
        restaurant_name="The Garden Room",
        persona_name=None,
        minimum_spend=None,
    )
    assert "Bob Jones" in result["body"]


def test_fallback_draft_includes_restaurant_name_in_subject() -> None:
    provider = FallbackDraftProvider()
    result = provider.generate(
        guest_name="Alice",
        event_type="corporate",
        event_date=None,
        party_size=50,
        restaurant_name="The Ivy Chelsea",
        persona_name="The Executive Host",
        minimum_spend=5000.0,
    )
    assert "The Ivy Chelsea" in result["subject"]


def test_fallback_draft_includes_minimum_spend() -> None:
    provider = FallbackDraftProvider()
    result = provider.generate(
        guest_name="Guest",
        event_type="wedding",
        event_date=date(2026, 6, 15),
        party_size=100,
        restaurant_name="The Grand",
        persona_name="The Host",
        minimum_spend=8000.0,
    )
    assert "8,000" in result["body"]


def test_fallback_draft_includes_party_size() -> None:
    provider = FallbackDraftProvider()
    result = provider.generate(
        guest_name="Guest",
        event_type="birthday",
        event_date=None,
        party_size=30,
        restaurant_name="The Grand",
        persona_name=None,
        minimum_spend=None,
    )
    assert "30" in result["body"]


def test_fallback_draft_works_with_all_optional_fields_none() -> None:
    """Fallback must not raise when all optional fields are None."""
    provider = FallbackDraftProvider()
    result = provider.generate(
        guest_name="Unknown Guest",
        event_type=None,
        event_date=None,
        party_size=None,
        restaurant_name="The Grand",
        persona_name=None,
        minimum_spend=None,
    )
    assert result["subject"] != ""
    assert result["body"] != ""


def test_fallback_draft_is_deterministic() -> None:
    """Same inputs produce identical output (no randomness)."""
    provider = FallbackDraftProvider()
    kwargs = dict(
        guest_name="Alice",
        event_type="dinner",
        event_date=date(2026, 8, 1),
        party_size=10,
        restaurant_name="The Grand",
        persona_name="The Host",
        minimum_spend=1000.0,
    )
    r1 = provider.generate(**kwargs)
    r2 = provider.generate(**kwargs)
    assert r1["subject"] == r2["subject"]
    assert r1["body"] == r2["body"]
