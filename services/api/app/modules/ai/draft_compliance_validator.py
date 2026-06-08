"""Draft Compliance Validator (RESP-008, strengthened in RESP-012, RESP-020, RESP-025).

Validates generated draft emails against the availability contract, spend rules,
and prompt constraints before the draft is shown to staff or sent to guests.

All checks are deterministic — no LLM calls are made.

RESP-008 checks:
  1. Availability over-claim
  2. Invented alternatives when CONFIRMED_UNAVAILABLE
  3. Unconfirmed times stated as agreed
  4. Minimum spend described as recommended/optional
  5. Fake booking form links

RESP-012 additional checks:
  6. Hosting language when availability NOT_CHECKED
  7. Invented SLA commitment (e.g. "within 24 hours")
  8. Invented clarification questions when none are allowed
  9. Forbidden topic mentions: menu, dietary, special touches, call scheduling

RESP-020 additional checks:
  10. Unavailable room described as suitable or perfect (CONFIRMED_UNAVAILABLE)

RESP-025 additional checks:
  10b. Room suitability language extended to NOT_CHECKED contract state

Usage::

    from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext

    ctx = ValidationContext(
        availability_contract="NOT_CHECKED",
        clarification_questions=[],
        confirmed_minimum_spend=1500.0,
        party_size=20,
    )
    result = DraftComplianceValidator.validate(draft_text, ctx)
    # result.passed → False
    # result.violations → ["Draft confirms availability when contract is NOT_CHECKED"]
    # result.unsafe_to_send → True
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── Input context ──────────────────────────────────────────────────────────────


@dataclass
class ValidationContext:
    """Inputs required to validate a draft response.

    Attributes:
        availability_contract: One of the five V4 contract states.
        clarification_questions: Questions that are allowed in the draft (may be empty).
        confirmed_minimum_spend: Venue-confirmed minimum spend (or None).
        party_size: Expected number of guests (or None).
        prohibited_times: Time strings extracted from the guest message (unconfirmed).
        response_goal: The response goal assigned to this draft.
    """

    availability_contract: str = "NOT_CHECKED"
    clarification_questions: list[str] = field(default_factory=list)
    confirmed_minimum_spend: float | None = None
    party_size: int | None = None
    prohibited_times: list[str] = field(default_factory=list)
    response_goal: str = ""
    # RESP-012: additional context flags
    alternatives_allowed: bool = False  # True only when explicit alternatives provided
    time_confirmed: bool = False        # True when a specific time is confirmed by venue
    allow_menu_discussion: bool = False
    allow_special_touches: bool = False
    allow_call_scheduling: bool = False


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class ComplianceResult:
    """Result of DraftComplianceValidator.validate().

    Attributes:
        passed:         True when no violations were detected.
        violations:     List of human-readable violation descriptions.
        unsafe_to_send: True when any violation prevents sending the draft.
    """

    passed: bool
    violations: list[str]
    unsafe_to_send: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "unsafe_to_send": self.unsafe_to_send,
        }


# ── Patterns ───────────────────────────────────────────────────────────────────

# Phrases that confirm availability to the guest
_AVAILABILITY_CONFIRM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:is|are)\s+available\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:do|can)\s+have\s+availability\b", re.IGNORECASE),
    re.compile(r"\bconfirm(?:ed)?\s+(?:your|the)\s+(?:date|booking|reservation)\b", re.IGNORECASE),
    re.compile(r"\bpleas(?:ed|ure)\s+to\s+confirm\b", re.IGNORECASE),
    re.compile(r"\bdate\s+is\s+free\b", re.IGNORECASE),
    re.compile(r"\bhave\s+(?:the\s+)?(?:date|room|slot)\s+available\b", re.IGNORECASE),
]

# Phrases that suggest alternative dates when the slot is unavailable
# (LLM should acknowledge but never invent alternatives)
# RESP-020: extended with "explore other options", "other options/slots/rooms"
_ALTERNATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\balternative(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\bhow\s+about\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+about\b", re.IGNORECASE),
    re.compile(r"\bother\s+(?:dates?|times?|options?|slots?|rooms?)\b", re.IGNORECASE),
    re.compile(r"\bdifferent\s+dates?\b", re.IGNORECASE),
    re.compile(r"\banother\s+(?:date|time|slot)\b", re.IGNORECASE),
    re.compile(r"\bwe\s+could\s+offer\b", re.IGNORECASE),
    re.compile(r"\bexplore\s+(?:other|alternative|different)\s+(?:options?|dates?|slots?)\b", re.IGNORECASE),
]

# Patterns for recommended/optional spend wording
_SPEND_SOFT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brecommended\s+(?:minimum\s+)?spend\b", re.IGNORECASE),
    re.compile(r"\boptional\s+(?:minimum\s+)?spend\b", re.IGNORECASE),
    re.compile(r"\bspend\s+(?:of\s+)?(?:is\s+)?optional\b", re.IGNORECASE),
    re.compile(r"\bsuggested\s+(?:minimum\s+)?spend\b", re.IGNORECASE),
]

# Patterns for placeholder / fake booking form links
_FAKE_URL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\[(?:form\s+)?link\]", re.IGNORECASE),
    re.compile(r"\[(?:booking\s+)?form\s+url\]", re.IGNORECASE),
    re.compile(r"(?:https?://)?(?:www\.)?(?:yourvenue|example|yourwebsite|link\s*here)", re.IGNORECASE),
    re.compile(r"\bclick\s+here\s+to\s+(?:book|fill|complete)\b", re.IGNORECASE),
]

# RESP-012: Hosting language — implies venue is ready to host when NOT_CHECKED
_HOSTING_LANGUAGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\blooking\s+forward\s+to\s+hosting\b", re.IGNORECASE),
    re.compile(r"\bwould\s+be\s+perfect\s+for\b", re.IGNORECASE),
    re.compile(r"\bperfect\s+for\s+your\s+(?:event|party|group|occasion|celebration)\b", re.IGNORECASE),
    re.compile(r"\bcan\s+(?:certainly|absolutely)\s+host\b", re.IGNORECASE),
    re.compile(r"\bdelighted\s+to\s+host\b", re.IGNORECASE),
    re.compile(r"\bwould\s+love\s+to\s+host\b", re.IGNORECASE),
]

# RESP-012: Invented SLA commitments
_SLA_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bwithin\s+(?:the\s+next\s+)?\d+\s+hours?\b", re.IGNORECASE),
    re.compile(r"\bwithin\s+(?:the\s+next\s+)?\d+\s+(?:business\s+)?days?\b", re.IGNORECASE),
    re.compile(r"\bby\s+(?:end\s+of\s+)?(?:today|tomorrow|this\s+(?:morning|afternoon|evening))\b", re.IGNORECASE),
    re.compile(r"\bshortly\s+(?:after|following)\b", re.IGNORECASE),
    re.compile(r"\brespond\s+(?:to\s+you\s+)?(?:by|within|before)\b", re.IGNORECASE),
]

# RESP-012: Invented questions — a question mark where none was authorised
# Detects sentence-ending question marks (not just any ? in quoted text)
_QUESTION_SENTENCE_PATTERN = re.compile(r"[A-Z][^.!?]*\?", re.DOTALL)

# RESP-012: Forbidden topic — menu and dietary discussion
# RESP-020: extended with "menu preferences"
_MENU_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bmenu\s+(?:options?|choice|choices|selection|discussion|preferences?)\b", re.IGNORECASE),
    re.compile(r"\bdiscuss\s+(?:the\s+)?menu\b", re.IGNORECASE),
    re.compile(r"\bdietary\s+(?:requirements?|restrictions?|needs?|preferences?)\b", re.IGNORECASE),
    re.compile(r"\bfood\s+(?:options?|preferences?|choices?)\b", re.IGNORECASE),
]

# RESP-012: Forbidden topic — special touches and personalisation
# RESP-020: extended with "special details/elements", "personalisation"
_SPECIAL_TOUCHES_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bspecial\s+touch(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bspecial\s+(?:details?|elements?|arrangements?|features?)\b", re.IGNORECASE),
    re.compile(r"\bpersonal\s+touch(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bpersonalis(?:e|ed|ation|ing)\b", re.IGNORECASE),
    re.compile(r"\bdecorations?\b", re.IGNORECASE),
    re.compile(r"\bfloral\s+arrangement\b", re.IGNORECASE),
    re.compile(r"\bspecial\s+arrangement\b", re.IGNORECASE),
]

# RESP-020: Room suitability language when slot is CONFIRMED_UNAVAILABLE
_ROOM_SUITABILITY_UNAVAILABLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bperfect\s+for\b", re.IGNORECASE),
    re.compile(r"\bideal\s+for\b", re.IGNORECASE),
    re.compile(r"\bwell[\s-]+suited\s+(?:to|for)\b", re.IGNORECASE),
    re.compile(r"\bexcellent\s+(?:choice|venue|space|room)\s+for\b", re.IGNORECASE),
    re.compile(r"\b(?:have\s+the\s+)?space\s+and\s+expertise\s+to\b", re.IGNORECASE),
]

# RESP-012: Forbidden topic — call scheduling
_CALL_SCHEDULING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\barrange\s+a\s+call\b", re.IGNORECASE),
    re.compile(r"\bschedule\s+a\s+call\b", re.IGNORECASE),
    re.compile(r"\bhop\s+on\s+a\s+call\b", re.IGNORECASE),
    re.compile(r"\bgive\s+(?:us|me)\s+a\s+(?:call|ring)\b", re.IGNORECASE),
    re.compile(r"\bcall\s+us\s+(?:on|at)\b", re.IGNORECASE),
    re.compile(r"\bspeak\s+(?:on|over)\s+the\s+phone\b", re.IGNORECASE),
]


# ── Validator ──────────────────────────────────────────────────────────────────


class DraftComplianceValidator:
    """Deterministic validator for generated draft emails.

    Call DraftComplianceValidator.validate(draft_text, context) to receive a
    ComplianceResult.  All checks are string-pattern based — no LLM calls.
    """

    @classmethod
    def validate(cls, draft_text: str, context: ValidationContext) -> ComplianceResult:
        """Validate a draft response against the supplied context.

        Args:
            draft_text: The raw text of the generated draft email.
            context:    Validation inputs (availability contract, spend, etc.).

        Returns:
            ComplianceResult with passed, violations, and unsafe_to_send.
        """
        violations: list[str] = []

        # Run all checks
        cls._check_availability_overclaim(draft_text, context, violations)
        cls._check_confirmed_unavailable_alternatives(draft_text, context, violations)
        cls._check_unconfirmed_times(draft_text, context, violations)
        cls._check_spend_soft_language(draft_text, context, violations)
        cls._check_fake_urls(draft_text, violations)
        # RESP-012 additional checks
        cls._check_hosting_language(draft_text, context, violations)
        cls._check_invented_sla(draft_text, violations)
        cls._check_invented_questions(draft_text, context, violations)
        cls._check_forbidden_topics(draft_text, context, violations)
        # RESP-020 additional checks
        cls._check_unavailable_room_suitability(draft_text, context, violations)

        passed = len(violations) == 0
        return ComplianceResult(
            passed=passed,
            violations=violations,
            unsafe_to_send=not passed,
        )

    # ── Individual checks ──────────────────────────────────────────────────────

    @classmethod
    def _check_availability_overclaim(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft confirms availability when the contract is not CONFIRMED_AVAILABLE."""
        contract = context.availability_contract
        if contract == "CONFIRMED_AVAILABLE":
            return  # Confirming is correct
        for pattern in _AVAILABILITY_CONFIRM_PATTERNS:
            if pattern.search(text):
                violations.append(
                    f"Draft appears to confirm availability but contract state is {contract}. "
                    "Availability must not be confirmed until the venue system returns "
                    "CONFIRMED_AVAILABLE."
                )
                return  # One violation per category

    @classmethod
    def _check_confirmed_unavailable_alternatives(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft invents alternatives when the slot is CONFIRMED_UNAVAILABLE."""
        if context.availability_contract != "CONFIRMED_UNAVAILABLE":
            return
        for pattern in _ALTERNATIVE_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft suggests alternative dates or options when the slot is "
                    "CONFIRMED_UNAVAILABLE. Alternatives must not be invented — "
                    "only use alternatives explicitly provided in the context."
                )
                return

    @classmethod
    def _check_unconfirmed_times(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft states a specific time that came from an unconfirmed guest preference."""
        if not context.prohibited_times:
            return
        for time_str in context.prohibited_times:
            # Normalise: strip whitespace, lowercase for comparison
            time_norm = time_str.strip().lower()
            # Check if the draft uses a phrase that confirms the time
            confirm_time_pattern = re.compile(
                r"(?:at|from|starting\s+at|beginning\s+at|for)\s+"
                + re.escape(time_norm),
                re.IGNORECASE,
            )
            if confirm_time_pattern.search(text.lower()):
                violations.append(
                    f"Draft appears to confirm the time '{time_str}' as agreed, but this "
                    "time came from the guest message and has not been confirmed by the venue."
                )
                return

    @classmethod
    def _check_spend_soft_language(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft describes minimum spend as recommended or optional."""
        if context.confirmed_minimum_spend is None:
            return  # No spend to validate
        for pattern in _SPEND_SOFT_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft describes minimum spend as recommended or optional. "
                    "Minimum spend is a MANDATORY requirement and must be described as such."
                )
                return

    @classmethod
    def _check_fake_urls(
        cls,
        text: str,
        violations: list[str],
    ) -> None:
        """Fail if the draft contains placeholder or invented booking form links."""
        for pattern in _FAKE_URL_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft contains a placeholder or invented booking form link. "
                    "No URL or form link may appear unless explicitly provided in the context."
                )
                return

    # ── RESP-012 additional checks ──────────────────────────────────────────

    @classmethod
    def _check_hosting_language(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft uses hosting language when availability is NOT_CHECKED."""
        if context.availability_contract != "NOT_CHECKED":
            return
        for pattern in _HOSTING_LANGUAGE_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft uses hosting language (e.g. 'looking forward to hosting', "
                    "'would be perfect for') when availability has not been checked. "
                    "Hosting language must not be used until the contract state is "
                    "CONFIRMED_AVAILABLE."
                )
                return

    @classmethod
    def _check_invented_sla(
        cls,
        text: str,
        violations: list[str],
    ) -> None:
        """Fail if the draft commits to a specific response timeline."""
        for pattern in _SLA_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft contains an invented SLA commitment (e.g. 'within 24 hours', "
                    "'by tomorrow'). No response-time commitment may be made unless "
                    "explicitly provided in the context."
                )
                return

    @classmethod
    def _check_invented_questions(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft contains questions when no clarification questions were authorised."""
        if context.clarification_questions:
            return  # Questions are authorised
        matches = _QUESTION_SENTENCE_PATTERN.findall(text)
        if matches:
            violations.append(
                "Draft contains a question but no clarification questions were provided "
                "in the context. Questions must not be invented — only use the approved "
                "clarification questions."
            )

    @classmethod
    def _check_forbidden_topics(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft discusses topics not allowed by the context flags."""
        if not context.allow_menu_discussion:
            for pattern in _MENU_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        "Draft discusses menu or dietary requirements but this topic "
                        "is not permitted in the current response context."
                    )
                    break
        if not context.allow_special_touches:
            for pattern in _SPECIAL_TOUCHES_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        "Draft mentions special touches or decorations but this topic "
                        "is not permitted in the current response context."
                    )
                    break
        if not context.allow_call_scheduling:
            for pattern in _CALL_SCHEDULING_PATTERNS:
                if pattern.search(text):
                    violations.append(
                        "Draft invites the guest to schedule a call but call scheduling "
                        "is not permitted in the current response context."
                    )
                    break

    # ── RESP-020 additional checks ──────────────────────────────────────────

    @classmethod
    def _check_unavailable_room_suitability(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if the draft claims room suitability when availability is not confirmed.

        Applies to CONFIRMED_UNAVAILABLE (slot fully booked) and NOT_CHECKED (availability
        not yet verified). In both cases the response must not pre-sell the room as perfect
        or ideal — availability has not been established.

        RESP-020: originally CONFIRMED_UNAVAILABLE only.
        RESP-025: extended to NOT_CHECKED.
        """
        contract = context.availability_contract
        if contract not in ("CONFIRMED_UNAVAILABLE", "NOT_CHECKED"):
            return
        for pattern in _ROOM_SUITABILITY_UNAVAILABLE_PATTERNS:
            if pattern.search(text):
                violations.append(
                    f"Draft describes the room or space as suitable or perfect for the guest's "
                    f"event when the availability contract is {contract}. Room suitability "
                    "language must not be used before availability is confirmed."
                )
                return
