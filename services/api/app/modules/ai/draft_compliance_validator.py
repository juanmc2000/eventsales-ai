"""Draft Compliance Validator (RESP-008).

Validates generated draft emails against the availability contract, spend rules,
and prompt constraints before the draft is shown to staff or sent to guests.

All checks are deterministic — no LLM calls are made.

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
_ALTERNATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\balternative(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\bhow\s+about\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+about\b", re.IGNORECASE),
    re.compile(r"\bother\s+dates?\b", re.IGNORECASE),
    re.compile(r"\bdifferent\s+dates?\b", re.IGNORECASE),
    re.compile(r"\banother\s+(?:date|time|slot)\b", re.IGNORECASE),
    re.compile(r"\bwe\s+could\s+offer\b", re.IGNORECASE),
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
