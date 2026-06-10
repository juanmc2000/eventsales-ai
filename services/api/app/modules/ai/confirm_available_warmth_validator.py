"""CONFIRM_AVAILABLE Warmth Sentence Validator (RESP-040).

Validates the optional LLM-generated warmth sentence before it is inserted
into a deterministic CONFIRM_AVAILABLE draft.

The warmth sentence must be:
  - A single sentence (no full-stop mid-sentence allowed)
  - 20 words or fewer
  - Free of all operational claims

If validation fails the sentence is silently dropped — the deterministic
draft is still safe without it.

Usage::

    from app.modules.ai.confirm_available_warmth_validator import WarmthSentenceValidator

    result = WarmthSentenceValidator.validate("That sounds like a lovely birthday celebration.")
    # result.passed → True

    result = WarmthSentenceValidator.validate("We can discuss menu options to suit your group.")
    # result.passed → False
    # result.violation_code → "forbidden_topic_menu"
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class WarmthValidationResult:
    """Result of WarmthSentenceValidator.validate().

    Attributes:
        passed:         True when the sentence is safe to include.
        violation_code: Short code identifying the first violation, or None.
        violation_msg:  Human-readable description of the violation, or None.
    """

    passed: bool
    violation_code: str | None = None
    violation_msg: str | None = None


# ── Forbidden patterns ─────────────────────────────────────────────────────────

# Timing discussion
_TIMING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", re.IGNORECASE),
    re.compile(r"\bpreferred?\s+timing\b", re.IGNORECASE),
    re.compile(r"\bdiscuss\s+(?:the\s+)?timing\b", re.IGNORECASE),
    re.compile(r"\btiming\s+(?:for|of)\s+(?:the\s+)?(?:event|evening|dinner|lunch)\b", re.IGNORECASE),
    re.compile(r"\barrival\s+time\b", re.IGNORECASE),
    re.compile(r"\bstart\s+time\b", re.IGNORECASE),
]

# Menu / dietary
_MENU_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bmenu\b", re.IGNORECASE),
    re.compile(r"\bdietary\b", re.IGNORECASE),
    re.compile(r"\bfood\s+(?:options?|preferences?|choices?)\b", re.IGNORECASE),
    re.compile(r"\bcuisine\b", re.IGNORECASE),
    re.compile(r"\bdishes?\b", re.IGNORECASE),
]

# Special touches / decorations
_SPECIAL_TOUCHES_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bspecial\s+touch(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bpersonal\s+touch(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bpersonalis(?:e|ed|ation|ing)\b", re.IGNORECASE),
    re.compile(r"\bdecorations?\b", re.IGNORECASE),
    re.compile(r"\bfloral\b", re.IGNORECASE),
    re.compile(r"\bspecial\s+arrangement\b", re.IGNORECASE),
]

# Booking form references
_BOOKING_FORM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bbooking\s+form\b", re.IGNORECASE),
    re.compile(r"\bfill\s+(?:in|out)\b", re.IGNORECASE),
    re.compile(r"\bcomplete\s+(?:the|a)\s+form\b", re.IGNORECASE),
    re.compile(r"\bsubmit\s+(?:a|the)?\s*form\b", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\[(?:form|link|url)\]", re.IGNORECASE),
]

# Call scheduling
_CALL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcall\b", re.IGNORECASE),
    re.compile(r"\bphone\b", re.IGNORECASE),
    re.compile(r"\bspeak\s+(?:on|over)\b", re.IGNORECASE),
    re.compile(r"\bschedule\s+a\s+(?:call|chat)\b", re.IGNORECASE),
    re.compile(r"\bhop\s+on\b", re.IGNORECASE),
]

# Availability claims
_AVAILABILITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bconfirm(?:ed)?\s+(?:your|the)\s+(?:date|booking|slot|availability)\b", re.IGNORECASE),
    re.compile(r"\bis\s+available\b", re.IGNORECASE),
    re.compile(r"\bhave\s+availability\b", re.IGNORECASE),
    re.compile(r"\bdate\s+is\s+free\b", re.IGNORECASE),
]

# Pricing claims
_PRICING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"£\s*\d+", re.IGNORECASE),
    re.compile(r"\bminimum\s+spend\b", re.IGNORECASE),
    re.compile(r"\bpricing\b", re.IGNORECASE),
    re.compile(r"\bcost\b", re.IGNORECASE),
    re.compile(r"\brate\b", re.IGNORECASE),
]

# Room suitability claims
_ROOM_SUITABILITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bperfect\s+for\b", re.IGNORECASE),
    re.compile(r"\bideal\s+for\b", re.IGNORECASE),
    re.compile(r"\bwell[\s-]+suited\b", re.IGNORECASE),
    re.compile(r"\bexcellent\s+(?:choice|venue|space|room)\b", re.IGNORECASE),
    re.compile(r"\broom\b", re.IGNORECASE),
    re.compile(r"\bspace\b", re.IGNORECASE),
    re.compile(r"\bvenue\b", re.IGNORECASE),
]

# ── Validator ─────────────────────────────────────────────────────────────────


class WarmthSentenceValidator:
    """Validates the optional LLM warmth sentence for CONFIRM_AVAILABLE drafts.

    A valid warmth sentence:
      - Is a single sentence
      - Contains at most 20 words
      - Makes no operational claims (timing, menu, dietary, special touches,
        booking forms, calls, availability, pricing, room suitability)

    On failure the sentence should be discarded — do not retry.
    """

    _MAX_WORDS = 20

    @classmethod
    def validate(cls, text: str) -> WarmthValidationResult:
        """Validate a candidate warmth sentence.

        Args:
            text: The raw warmth sentence from the LLM.

        Returns:
            WarmthValidationResult with passed=True when the sentence is safe.
        """
        if not text or not text.strip():
            return WarmthValidationResult(
                passed=False,
                violation_code="empty",
                violation_msg="Warmth sentence is empty.",
            )

        sentence = text.strip()

        # Must be a single sentence — detect multiple sentences via sentence-ending punctuation
        if cls._has_multiple_sentences(sentence):
            return WarmthValidationResult(
                passed=False,
                violation_code="multiple_sentences",
                violation_msg="Warmth sentence contains more than one sentence.",
            )

        # Must not exceed max word count
        word_count = len(sentence.split())
        if word_count > cls._MAX_WORDS:
            return WarmthValidationResult(
                passed=False,
                violation_code="too_long",
                violation_msg=(
                    f"Warmth sentence is {word_count} words — maximum is {cls._MAX_WORDS}."
                ),
            )

        # Check forbidden patterns in order of severity
        checks: list[tuple[str, str, list[re.Pattern[str]]]] = [
            ("forbidden_topic_timing", "Warmth sentence mentions timing.", _TIMING_PATTERNS),
            ("forbidden_topic_menu", "Warmth sentence mentions menu or dietary.", _MENU_PATTERNS),
            ("forbidden_topic_special_touches", "Warmth sentence mentions special touches.", _SPECIAL_TOUCHES_PATTERNS),
            ("forbidden_topic_booking_form", "Warmth sentence mentions a booking form or link.", _BOOKING_FORM_PATTERNS),
            ("forbidden_topic_call", "Warmth sentence mentions a call or phone contact.", _CALL_PATTERNS),
            ("forbidden_topic_availability", "Warmth sentence makes an availability claim.", _AVAILABILITY_PATTERNS),
            ("forbidden_topic_pricing", "Warmth sentence mentions pricing or spend.", _PRICING_PATTERNS),
            ("forbidden_topic_room_suitability", "Warmth sentence mentions room or space suitability.", _ROOM_SUITABILITY_PATTERNS),
        ]

        for code, msg, patterns in checks:
            for pattern in patterns:
                if pattern.search(sentence):
                    return WarmthValidationResult(
                        passed=False,
                        violation_code=code,
                        violation_msg=msg,
                    )

        return WarmthValidationResult(passed=True)

    @staticmethod
    def _has_multiple_sentences(text: str) -> bool:
        """Return True when the text contains more than one sentence.

        A sentence boundary is detected by a terminal punctuation character
        (. ! ?) that is followed by a space and an uppercase letter, or
        by a second occurrence of terminal punctuation.
        """
        # Strip trailing punctuation so a clean one-sentence ending doesn't count
        stripped = text.rstrip(".!? ")

        # Check for internal sentence-ending punctuation followed by space + word
        _boundary = re.compile(r"[.!?]\s+[A-Z]")
        if _boundary.search(stripped):
            return True

        # Check for two or more terminal punctuation marks
        terminal_count = len(re.findall(r"[.!?]", stripped))
        if terminal_count >= 2:
            return True

        return False
