"""Draft Compliance Validator (RESP-008, strengthened in RESP-012, RESP-020, RESP-025, RESP-026, RESP-027, RESP-033, RESP-052, RESP-053, RESP-062).

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

RESP-026 additional checks:
  11. Required copy block missing or paraphrased (when required_opening_phrase is set)

RESP-027 additional checks:
  12. Internal section labels leaked into the customer-facing draft

RESP-031 calibrations:
  - For CONFIRM_AVAILABLE, copy block check uses semantic validation (availability
    confirmed) instead of verbatim opening phrase — reduces false failures from
    harmless paraphrases while preserving all commercial-safety checks.
  - Mandatory minimum spend, unavailable statement, booking form URL, and date
    clarification remain strictly verbatim.

RESP-033 additional checks:
  13. Structured forbidden-topic violations (code, severity, matched_text)
      Covers: timing discussion, menu, dietary, special touches, call/chat/phone,
      alternative dates (via alternatives_allowed flag)

RESP-052 additional checks:
  14. Room pre-commitment in ACKNOWLEDGE_AND_CHECK_AVAILABILITY responses
      Forbidden: specific room names, "recommended room", capacity promises,
      suitability promises ("would be ideal", "perfect for your group").
RESP-053 additional checks:
  14. Invented room name across all response goals.
      If ValidationContext.known_room_names is provided and a room name in the
      draft does not match any known name (case-insensitive), it is flagged as
      an invented room name with violation code "invented_room_name".

RESP-062 additional checks:
  15. Customer name consistency guard.
      If ValidationContext.expected_customer_name is set, the draft greeting
      must match the expected name (case-insensitive, prefix-allows).  A mismatch
      is a high-trust failure.

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

from app.modules.ai.customer_name_validator import CustomerNameConsistencyValidator


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
    allow_timing_discussion: bool = False  # RESP-033: True only when timing explicitly allowed
    # RESP-026: required copy block (normalized verbatim match enforced when set)
    required_opening_phrase: str | None = None
    # RESP-034: rendered approved block texts for post-extension detection
    approved_blocks: list[str] = field(default_factory=list)
    # RESP-053: known room names for the restaurant — used to detect invented room names
    # If empty, the invented-room-name check is skipped (caller has no room context)
    known_room_names: list[str] = field(default_factory=list)
    # RESP-062: expected customer first name for greeting consistency check
    # If None or empty, the name check is skipped
    expected_customer_name: str | None = None


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class ViolationDetail:
    """RESP-033: Structured violation record with code, severity, and matched text.

    Attributes:
        code:         Short identifier for the violation type (e.g. "forbidden_topic_menu").
        severity:     "high" | "medium" | "low"
        matched_text: The text fragment that triggered the violation (or empty string).
        message:      Human-readable description of the violation.
    """

    code: str
    severity: str  # "high" | "medium" | "low"
    matched_text: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "matched_text": self.matched_text,
            "message": self.message,
        }


@dataclass
class ComplianceResult:
    """Result of DraftComplianceValidator.validate().

    Attributes:
        passed:              True when no violations were detected.
        violations:          List of human-readable violation descriptions.
        unsafe_to_send:      True when any violation prevents sending the draft.
        structured_violations: RESP-033 structured violation records (code, severity, matched_text).
    """

    passed: bool
    violations: list[str]
    unsafe_to_send: bool
    structured_violations: list[ViolationDetail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "unsafe_to_send": self.unsafe_to_send,
            "structured_violations": [v.to_dict() for v in self.structured_violations],
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

# RESP-033: Timing-discussion topic — generic timing language (distinct from specific time mentions)
# Only covers clearly topic-level timing discussion phrases, not incidental time references.
_TIMING_LANGUAGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bpreferred?\s+timing\b", re.IGNORECASE),
    re.compile(r"\bdiscuss\s+(?:the\s+)?timing\b", re.IGNORECASE),
    re.compile(r"\btimings?\s+(?:for|of)\s+(?:the\s+)?(?:event|evening|dinner|lunch)\b", re.IGNORECASE),
    re.compile(r"\btiming\s+preferences?\b", re.IGNORECASE),
]

# RESP-032/RESP-055: Subject-line patterns that must not appear in the draft body.
# RESP-055: extended to cover "Re:" and "Email subject:" prefixes (ACKNOWLEDGE leakage).
_SUBJECT_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\*{0,2}Subject\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\*{0,2}Re\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\*{0,2}Email\s+subject\s*:", re.IGNORECASE | re.MULTILINE),
]

# RESP-027: Internal section labels that must not appear in customer-facing drafts
_SECTION_LABEL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\*\*Opening\*\*", re.IGNORECASE),
    re.compile(r"\*\*Enquiry\s+summary\*\*", re.IGNORECASE),
    re.compile(r"\*\*Availability\s+confirmation\*\*", re.IGNORECASE),
    re.compile(r"\*\*Booking\s+next\s+step\*\*", re.IGNORECASE),
    re.compile(r"\*\*Sign[\s-]+off\*\*", re.IGNORECASE),
    re.compile(r"\*\*Next\s+steps?\*\*", re.IGNORECASE),
    re.compile(r"\*\*Closing\*\*", re.IGNORECASE),
]

# RESP-053: Pattern for extracting named room/space references from draft text.
# Matches names like "The Garden Room", "Private Dining Room", "Rooftop Suite",
# "Crystal Ballroom", "Executive Lounge", "Loft Hall", "Sunset Terrace".
# Used to compare against ValidationContext.known_room_names.
_ROOM_NAME_PATTERN = re.compile(
    r"\b(?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
    r"(?:Room|Suite|Hall|Lounge|Terrace|Ballroom|Loft|Space|Bar|Gallery|Studio)\b"
)

# RESP-012: Forbidden topic — call scheduling
_CALL_SCHEDULING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\barrange\s+a\s+call\b", re.IGNORECASE),
    re.compile(r"\bschedule\s+a\s+call\b", re.IGNORECASE),
    re.compile(r"\bhop\s+on\s+a\s+call\b", re.IGNORECASE),
    re.compile(r"\bgive\s+(?:us|me)\s+a\s+(?:call|ring)\b", re.IGNORECASE),
    re.compile(r"\bcall\s+us\s+(?:on|at)\b", re.IGNORECASE),
    re.compile(r"\bspeak\s+(?:on|over)\s+the\s+phone\b", re.IGNORECASE),
]

# RESP-052: Room pre-commitment language — forbidden in ACKNOWLEDGE_AND_CHECK_AVAILABILITY
# Covers specific room name patterns, suitability promises, and capacity promises.
_ACKNOWLEDGE_ROOM_NAME_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Room\b"
)
_ACKNOWLEDGE_ROOM_PRECOMMITMENT_PATTERNS: list[re.Pattern[str]] = [
    _ACKNOWLEDGE_ROOM_NAME_PATTERN,
    # Suitability / pre-commitment phrases
    re.compile(r"\bwould\s+be\s+ideal\b", re.IGNORECASE),
    re.compile(r"\bperfect\s+for\s+your\s+(?:group|party|event|occasion|celebration)\b", re.IGNORECASE),
    re.compile(r"\brecommended\s+room\b", re.IGNORECASE),
    re.compile(r"\bsuitable\s+(?:room|venue)\b", re.IGNORECASE),
    # Capacity promises (e.g. "seats 30", "accommodates 40", "capacity for 20")
    re.compile(r"\b(?:seat|seats|seating|accommodate[sd]?|capacity\s+for)\s+\d+\b", re.IGNORECASE),
]

# RESP-052: Safe-context phrases that precede a room name without constituting pre-commitment.
# e.g. "We will check availability of the Terrace Room" is checking, not committing.
_ROOM_NAME_SAFE_CONTEXT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcheck(?:ing)?\s+(?:(?:the|a)\s+)?availability\b", re.IGNORECASE),
    re.compile(r"\bavailability\s+of\b", re.IGNORECASE),
    re.compile(r"\bcheck(?:ing)?\s+(?:if|whether)\b", re.IGNORECASE),
    re.compile(r"\blook(?:ing)?\s+into\s+(?:(?:the|a)\s+)?availability\b", re.IGNORECASE),
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
        structured_violations: list[ViolationDetail] = []

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
        # RESP-033: structured forbidden-topic check (also appends to violations)
        cls._check_forbidden_topics(draft_text, context, violations, structured_violations)
        # RESP-020 additional checks
        cls._check_unavailable_room_suitability(draft_text, context, violations)
        # RESP-026 additional checks
        cls._check_copy_block_compliance(draft_text, context, violations)
        # RESP-027 additional checks
        cls._check_section_labels(draft_text, violations)
        # RESP-032 additional checks
        cls._check_subject_line_in_body(draft_text, violations)
        # RESP-034 additional checks
        cls._check_copy_block_post_extension(draft_text, context, violations, structured_violations)
        # RESP-052 additional checks
        cls._check_acknowledge_room_precommitment(draft_text, context, violations)
        # RESP-053 additional checks
        cls._check_invented_room_names(draft_text, context, violations, structured_violations)
        # RESP-062 additional checks
        cls._check_customer_name_consistency(draft_text, context, violations)

        passed = len(violations) == 0
        return ComplianceResult(
            passed=passed,
            violations=violations,
            unsafe_to_send=not passed,
            structured_violations=structured_violations,
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
        """RESP-035: Fail if the draft mentions any time from an unconfirmed guest preference.

        Any mention of a prohibited time — not just confirming phrases — is a
        violation.  Prohibited times are extracted from the guest message and
        represent unconfirmed preferences; they must not appear anywhere in the
        generated response.

        Confirmed venue times will not be in prohibited_times, so they are
        unaffected by this check.
        """
        if not context.prohibited_times:
            return
        for time_str in context.prohibited_times:
            time_norm = time_str.strip()
            any_mention_pattern = re.compile(re.escape(time_norm), re.IGNORECASE)
            if any_mention_pattern.search(text):
                violations.append(
                    f"Draft mentions the time '{time_str}', which is an unconfirmed guest "
                    "preference. Unconfirmed times must not appear anywhere in the response — "
                    "not even as a preference echo or soft reference."
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
        structured_violations: list[ViolationDetail] | None = None,
    ) -> None:
        """RESP-033: Fail if the draft discusses topics not allowed by the context flags.

        Appends human-readable messages to violations (backward-compatible).
        When structured_violations is provided, also appends ViolationDetail records
        with code, severity, and matched_text.
        """
        def _record(code: str, severity: str, matched_text: str, message: str) -> None:
            violations.append(message)
            if structured_violations is not None:
                structured_violations.append(ViolationDetail(
                    code=code,
                    severity=severity,
                    matched_text=matched_text,
                    message=message,
                ))

        if not context.allow_menu_discussion:
            for pattern in _MENU_PATTERNS:
                m = pattern.search(text)
                if m:
                    _record(
                        code="forbidden_topic_menu",
                        severity="high",
                        matched_text=m.group(0),
                        message=(
                            "Draft discusses menu or dietary requirements but this topic "
                            "is not permitted in the current response context."
                        ),
                    )
                    break
        if not context.allow_special_touches:
            for pattern in _SPECIAL_TOUCHES_PATTERNS:
                m = pattern.search(text)
                if m:
                    _record(
                        code="forbidden_topic_special_touches",
                        severity="medium",
                        matched_text=m.group(0),
                        message=(
                            "Draft mentions special touches or decorations but this topic "
                            "is not permitted in the current response context."
                        ),
                    )
                    break
        if not context.allow_call_scheduling:
            for pattern in _CALL_SCHEDULING_PATTERNS:
                m = pattern.search(text)
                if m:
                    _record(
                        code="forbidden_topic_call_scheduling",
                        severity="medium",
                        matched_text=m.group(0),
                        message=(
                            "Draft invites the guest to schedule a call but call scheduling "
                            "is not permitted in the current response context."
                        ),
                    )
                    break
        # RESP-033: timing discussion topic
        if not context.allow_timing_discussion:
            for pattern in _TIMING_LANGUAGE_PATTERNS:
                m = pattern.search(text)
                if m:
                    _record(
                        code="forbidden_topic_timing",
                        severity="high",
                        matched_text=m.group(0),
                        message=(
                            "Draft discusses timing or arrival time preferences but this topic "
                            "is not permitted until confirmed venue facts are established."
                        ),
                    )
                    break
        # RESP-033: alternative dates topic (via alternatives_allowed flag)
        # Skip CONFIRMED_UNAVAILABLE (own check) and CONFIRMED_AVAILABLE (alternatives OK)
        if not context.alternatives_allowed and context.availability_contract not in (
            "CONFIRMED_UNAVAILABLE",
            "CONFIRMED_AVAILABLE",
        ):
            for pattern in _ALTERNATIVE_PATTERNS:
                m = pattern.search(text)
                if m:
                    _record(
                        code="forbidden_topic_alternatives",
                        severity="high",
                        matched_text=m.group(0),
                        message=(
                            "Draft suggests alternative dates or options but alternatives "
                            "are not permitted in the current response context."
                        ),
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

    # ── RESP-026 additional checks ──────────────────────────────────────────

    @staticmethod
    def _normalise_for_comparison(text: str) -> str:
        """Strip markdown formatting and collapse whitespace for copy-block comparison.

        Removes bold/italic markers (**text**, *text*), strips leading/trailing
        whitespace, and collapses all internal whitespace runs to a single space.
        This allows formatting differences (e.g. extra newlines) to be ignored.
        """
        # Strip markdown bold/italic markers
        text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
        # Normalise all whitespace (newlines, tabs, multiple spaces) to single space
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    @classmethod
    def _check_copy_block_compliance(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """Fail if a required copy block is missing or paraphrased in the draft.

        RESP-026: When ValidationContext.required_opening_phrase is set, strict
        verbatim matching is enforced — EXCEPT for CONFIRM_AVAILABLE (RESP-031).

        RESP-031: For CONFIRM_AVAILABLE, semantic validation replaces verbatim:
        the draft must contain availability confirmation language (pattern-matched)
        rather than the exact approved phrase.  This avoids failing on harmless
        paraphrases while preserving all commercial-safety checks.

        Strict verbatim remains in force for:
          - CONFIRMED_UNAVAILABLE (unavailable statement must not be softened)
          - Minimum spend language (handled by _check_spend_soft_language)
          - Booking form URL (handled by _check_fake_urls)
          - Any goal other than CONFIRM_AVAILABLE
        """
        if not context.required_opening_phrase:
            return

        if context.response_goal == "CONFIRM_AVAILABLE":
            # RESP-031: semantic check — availability must be confirmed somewhere in the draft
            cls._check_confirm_available_semantic(text, violations)
            return

        normalised_draft = cls._normalise_for_comparison(text)
        normalised_required = cls._normalise_for_comparison(context.required_opening_phrase)
        if normalised_required not in normalised_draft:
            violations.append(
                "Draft is missing a required copy block. The approved opening phrase "
                f"'{context.required_opening_phrase[:80]}' (or its equivalent) must "
                "appear verbatim. Paraphrasing operational copy is not permitted."
            )

    @classmethod
    def _check_confirm_available_semantic(
        cls,
        text: str,
        violations: list[str],
    ) -> None:
        """RESP-031: semantic validation for CONFIRM_AVAILABLE drafts.

        Checks that the draft communicates availability confirmation without
        requiring the exact approved phrase verbatim.  A draft passes when at
        least one availability-confirm pattern matches.

        This check catches cases where the LLM omits all availability language
        (e.g. by starting with a sales pitch rather than confirming the date).
        """
        for pattern in _AVAILABILITY_CONFIRM_PATTERNS:
            if pattern.search(text):
                return  # Availability is confirmed — no violation
        violations.append(
            "CONFIRM_AVAILABLE draft does not appear to confirm availability. "
            "The response must clearly state that the date or slot is available. "
            "Approved phrases include: 'I'm delighted to confirm', "
            "'we have availability', 'pleased to confirm', 'date is free'."
        )

    # ── RESP-027 additional checks ──────────────────────────────────────────

    @classmethod
    def _check_section_labels(
        cls,
        text: str,
        violations: list[str],
    ) -> None:
        """Fail if internal section labels appear in the customer-facing draft.

        Labels such as **Opening** or **Sign-off** are internal structural markers
        used during prompt construction and must never appear in the email sent to guests.
        """
        for pattern in _SECTION_LABEL_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft contains an internal section label (e.g. **Opening**, "
                    "**Sign-off**) that must not appear in customer-facing emails. "
                    "Remove all structural headings from the draft body."
                )
                return  # One violation per category

    # ── RESP-032 additional checks ──────────────────────────────────────────

    @classmethod
    def _check_subject_line_in_body(
        cls,
        text: str,
        violations: list[str],
    ) -> None:
        """Fail if a subject line appears anywhere in the draft body.

        Patterns such as 'Subject: ...' or '**Subject: ...**' must not appear
        in the email body — the subject is set separately by the caller.
        """
        for pattern in _SUBJECT_LINE_PATTERNS:
            if pattern.search(text):
                violations.append(
                    "Draft contains a subject line in the email body "
                    "(e.g. 'Subject: ...' or '**Subject: ...**'). "
                    "Remove it — the subject field is set separately."
                )
                return  # One violation per category

    # ── RESP-034 additional checks ──────────────────────────────────────────

    # Forbidden-extension patterns: content that must not follow an approved block
    _FORBIDDEN_EXTENSION_PATTERNS: list[re.Pattern[str]] = (
        _MENU_PATTERNS
        + _SPECIAL_TOUCHES_PATTERNS
        + _CALL_SCHEDULING_PATTERNS
        + _TIMING_LANGUAGE_PATTERNS
    )

    @classmethod
    def _check_copy_block_post_extension(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
        structured_violations: list[ViolationDetail] | None = None,
    ) -> None:
        """RESP-034: Fail if extra text is appended immediately after an approved copy block.

        For each block in context.approved_blocks, locate it in the normalised
        draft and extract the text that follows it up to the next paragraph break.
        If that trailing text is non-trivial (more than a salutation) AND mentions
        a forbidden topic, record a high-severity violation.
        """
        if not context.approved_blocks:
            return

        norm_draft = cls._normalise_for_comparison(text)

        for block_text in context.approved_blocks:
            norm_block = cls._normalise_for_comparison(block_text)
            if not norm_block:
                continue

            pos = norm_draft.find(norm_block)
            if pos == -1:
                continue  # Block not present — RESP-026 handles the missing-block case

            # Extract text immediately following this block up to the next sentence break
            after_pos = pos + len(norm_block)
            # Grab up to 250 normalised characters after the block
            trailing = norm_draft[after_pos:after_pos + 250].strip()
            if not trailing:
                continue  # Nothing follows the block

            # Skip if trailing is only a short salutation or sign-off
            if len(trailing.split()) <= 3:
                continue

            # Check for forbidden-topic content in the trailing text
            for pattern in cls._FORBIDDEN_EXTENSION_PATTERNS:
                m = pattern.search(trailing)
                if m:
                    message = (
                        "Draft extends an approved copy block with forbidden-topic language "
                        f"('{m.group(0)}'). No extra operational content may be appended "
                        "after an approved block — the block is the complete operational statement."
                    )
                    violations.append(message)
                    if structured_violations is not None:
                        structured_violations.append(ViolationDetail(
                            code="copy_block_post_extension",
                            severity="high",
                            matched_text=m.group(0),
                            message=message,
                        ))
                    return  # One violation per call

    # ── RESP-052 additional checks ──────────────────────────────────────────

    @classmethod
    def _check_acknowledge_room_precommitment(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """RESP-052: Fail if an ACKNOWLEDGE response contains room pre-commitment language.

        Before availability is confirmed, ACKNOWLEDGE_AND_CHECK_AVAILABILITY responses
        must not name specific rooms, imply room suitability, or promise capacity.
        Allowed: "I'll check availability" / "I'll check suitable space."
        Forbidden: room names, "would be ideal", "recommended room", capacity promises.
        """
        if context.response_goal != "ACKNOWLEDGE_AND_CHECK_AVAILABILITY":
            return
        # Only applies before availability is confirmed — no pre-commitment possible if already confirmed
        if context.availability_contract == "CONFIRMED_AVAILABLE":
            return
        for pattern in _ACKNOWLEDGE_ROOM_PRECOMMITMENT_PATTERNS:
            if pattern is _ACKNOWLEDGE_ROOM_NAME_PATTERN:
                # Room name in a safe "checking availability of [Room]" context is allowed.
                for m in pattern.finditer(text):
                    start = max(0, m.start() - 35)
                    preceding = text[start:m.start()]
                    if any(sp.search(preceding) for sp in _ROOM_NAME_SAFE_CONTEXT_PATTERNS):
                        continue  # Safe context — availability check, not pre-commitment
                    violations.append(
                        f"ACKNOWLEDGE response contains room pre-commitment language "
                        f"('{m.group(0)}'). Room names, suitability claims, and capacity "
                        "promises must not appear before availability is confirmed. "
                        "Use 'I'll check availability' or 'I'll check suitable space' instead."
                    )
                    return  # One violation per category
            else:
                m = pattern.search(text)
                if m:
                    violations.append(
                        f"ACKNOWLEDGE response contains room pre-commitment language "
                        f"('{m.group(0)}'). Room names, suitability claims, and capacity "
                        "promises must not appear before availability is confirmed. "
                        "Use 'I'll check availability' or 'I'll check suitable space' instead."
                    )
                    return  # One violation per category

    # ── RESP-053 additional checks ──────────────────────────────────────────

    @classmethod
    def _check_invented_room_names(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
        structured_violations: list[ViolationDetail] | None = None,
    ) -> None:
        """RESP-053: Fail if the draft names a room not present in known_room_names.

        Applies to all response goals.  If ValidationContext.known_room_names is
        empty, the check is skipped — the caller has not provided room context so
        validation is not possible.

        If a room name is detected in the draft that does not match any known room
        (case-insensitive), a structured violation with code "invented_room_name"
        is recorded.
        """
        if not context.known_room_names:
            return  # No room context — cannot validate room names

        known_lower = {name.strip().lower() for name in context.known_room_names}
        matches = _ROOM_NAME_PATTERN.findall(text)
        for match in matches:
            if match.strip().lower() not in known_lower:
                message = (
                    f"Draft mentions room '{match}' which is not in the known room list "
                    f"for this restaurant. Room names must match confirmed venue context — "
                    "invented room names must not appear in responses."
                )
                violations.append(message)
                if structured_violations is not None:
                    structured_violations.append(ViolationDetail(
                        code="invented_room_name",
                        severity="high",
                        matched_text=match,
                        message=message,
                    ))
                return  # One violation per check call

    # ── RESP-062 additional checks ─────────────────────────────────────────

    @classmethod
    def _check_customer_name_consistency(
        cls,
        text: str,
        context: ValidationContext,
        violations: list[str],
    ) -> None:
        """RESP-062: Fail if the draft greeting does not match the expected customer name.

        Delegates to CustomerNameConsistencyValidator.  The check is skipped when
        expected_customer_name is not set on the context.
        """
        if not context.expected_customer_name:
            return
        result = CustomerNameConsistencyValidator.validate(
            draft_text=text,
            expected_customer_name=context.expected_customer_name,
        )
        if not result.passed and result.violation:
            violations.append(result.violation)
