"""Tests for WarmthSentenceValidator (RESP-040, RESP-056).

Validates:
- Empty/multi-sentence/too-long rejection
- Forbidden topic rejection (timing, menu, special touches, calls, availability,
  pricing, room suitability)
- RESP-056: occasion consistency check (wrong-occasion sentence dropped)
- Known-occasion warmth passes; unknown occasion skips check
"""

from __future__ import annotations

import pytest

from app.modules.ai.confirm_available_warmth_validator import WarmthSentenceValidator


# ── Structural checks ─────────────────────────────────────────────────────────


class TestStructuralChecks:
    def test_empty_string_fails(self) -> None:
        result = WarmthSentenceValidator.validate("")
        assert result.passed is False
        assert result.violation_code == "empty"

    def test_whitespace_only_fails(self) -> None:
        result = WarmthSentenceValidator.validate("   ")
        assert result.passed is False
        assert result.violation_code == "empty"

    def test_multiple_sentences_fail(self) -> None:
        result = WarmthSentenceValidator.validate(
            "That sounds wonderful. We look forward to hosting you."
        )
        assert result.passed is False
        assert result.violation_code == "multiple_sentences"

    def test_too_long_fails(self) -> None:
        result = WarmthSentenceValidator.validate(
            "That sounds like a truly wonderful and special occasion that we are "
            "very much looking forward to celebrating together with you and your guests."
        )
        assert result.passed is False
        assert result.violation_code == "too_long"

    def test_single_sentence_short_passes(self) -> None:
        result = WarmthSentenceValidator.validate(
            "That sounds like a lovely birthday celebration."
        )
        assert result.passed is True


# ── Forbidden topic checks ────────────────────────────────────────────────────


class TestForbiddenTopics:
    def test_menu_mention_fails(self) -> None:
        result = WarmthSentenceValidator.validate("We can discuss the menu options for your group.")
        assert result.passed is False
        assert "menu" in result.violation_code

    def test_call_mention_fails(self) -> None:
        result = WarmthSentenceValidator.validate("Feel free to call us to discuss details.")
        assert result.passed is False
        assert "call" in result.violation_code

    def test_availability_claim_fails(self) -> None:
        result = WarmthSentenceValidator.validate("I'm pleased to confirm the date is available.")
        assert result.passed is False

    def test_pricing_mention_fails(self) -> None:
        result = WarmthSentenceValidator.validate("Our minimum spend is £2000 per table.")
        assert result.passed is False


# ── RESP-056: occasion consistency check ──────────────────────────────────────


class TestOccasionConsistency:
    """RESP-056: Warmth sentence must not mention a different occasion type."""

    def test_birthday_to_corporate_mismatch_fails(self) -> None:
        """Birthday occasion must not have corporate warmth (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "This sounds like a great corporate event.",
            occasion="birthday",
        )
        assert result.passed is False
        assert result.violation_code == "occasion_mismatch"

    def test_engagement_to_birthday_mismatch_fails(self) -> None:
        """Engagement occasion must not have birthday warmth (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "That sounds like a wonderful birthday celebration.",
            occasion="engagement",
        )
        assert result.passed is False
        assert result.violation_code == "occasion_mismatch"

    def test_birthday_warmth_passes_for_birthday_occasion(self) -> None:
        """Correct-occasion warmth passes (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "That sounds like a lovely birthday celebration.",
            occasion="birthday",
        )
        assert result.passed is True

    def test_neutral_warmth_passes_for_any_occasion(self) -> None:
        """Neutral warmth (no occasion keywords) passes for any occasion (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "That sounds like a wonderful occasion.",
            occasion="birthday",
        )
        assert result.passed is True

    def test_unknown_occasion_skips_check(self) -> None:
        """Unknown occasion skips consistency check — neutral warmth OK (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "That sounds like a wonderful corporate event.",
            occasion="unknown",
        )
        # No occasion to validate against — should pass if no other violations
        assert result.passed is True

    def test_no_occasion_provided_skips_check(self) -> None:
        """No occasion parameter skips consistency check (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "That sounds like a lovely birthday celebration.",
            occasion=None,
        )
        assert result.passed is True

    def test_anniversary_occasion_not_mislabelled_birthday(self) -> None:
        """Anniversary occasion must not have birthday warmth (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "Happy birthday to the guest of honour!",
            occasion="anniversary",
        )
        assert result.passed is False
        assert result.violation_code == "occasion_mismatch"

    def test_violation_message_names_both_occasions(self) -> None:
        """Violation message names the wrong occasion and the correct one (RESP-056)."""
        result = WarmthSentenceValidator.validate(
            "This sounds like a great corporate event.",
            occasion="birthday",
        )
        assert result.violation_msg is not None
        assert "corporate" in result.violation_msg.lower()
        assert "birthday" in result.violation_msg.lower()
