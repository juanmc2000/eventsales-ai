"""Customer Name Consistency Validator (RESP-062).

Detects greeting/name mismatches in draft email bodies before persistence.

A wrong customer name is a high-trust failure — it must block auto-send.

Rules:
- If expected_customer_name is set, the greeting name must match it.
- If expected_customer_name is unknown (None or empty), skip the check.
- Matching is case-insensitive and allows true-prefix variants
  (e.g. "Alex" matches "Alexander") by checking if either is a prefix of the other.

Usage::

    from app.modules.ai.customer_name_validator import CustomerNameConsistencyValidator

    result = CustomerNameConsistencyValidator.validate(
        draft_text="Dear Alice, thank you for your enquiry.",
        expected_customer_name="Bob",
    )
    # result.passed → False
    # result.violation → "Draft greets 'Alice' but expected customer name is 'Bob'."
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ── Greeting extraction ─────────────────────────────────────────────────────────

# Matches "Dear Alice,", "Dear Mr Smith,", "Hi Alice,", "Hello Alice,"
# Captures the first word after the salutation as the greeting name.
_GREETING_RE = re.compile(
    r"^\s*(?:Dear|Hi|Hello)\s+([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+)*)",
    re.MULTILINE | re.IGNORECASE,
)


# ── Result ─────────────────────────────────────────────────────────────────────


@dataclass
class NameConsistencyResult:
    """Result of CustomerNameConsistencyValidator.validate().

    Attributes:
        passed:          True when no name mismatch was detected.
        greeting_name:   The name extracted from the greeting, or None.
        expected_name:   The expected customer first name supplied to the validator.
        violation:       Human-readable violation message, or None when passed.
    """

    passed: bool
    greeting_name: str | None = None
    expected_name: str | None = None
    violation: str | None = None


# ── Validator ──────────────────────────────────────────────────────────────────


class CustomerNameConsistencyValidator:
    """Deterministic validator that checks the draft greeting matches the expected customer name.

    No LLM calls are made.
    """

    @staticmethod
    def extract_greeting_name(draft_text: str) -> str | None:
        """Extract the first name from the greeting line of a draft.

        Returns the first word of the salutation (e.g. "Alice" from "Dear Alice,"),
        or None when no recognised greeting is found.
        """
        match = _GREETING_RE.search(draft_text)
        if not match:
            return None
        full_salutation = match.group(1).strip()
        # Return only the first word (first name) for comparison
        return full_salutation.split()[0] if full_salutation else None

    @classmethod
    def validate(
        cls,
        draft_text: str,
        expected_customer_name: str | None,
    ) -> NameConsistencyResult:
        """Check that the draft greeting matches the expected customer name.

        Args:
            draft_text:             The draft email body text.
            expected_customer_name: The expected first name of the customer (or None).

        Returns:
            NameConsistencyResult with passed=True when names match or check is skipped.
        """
        if not expected_customer_name or not expected_customer_name.strip():
            return NameConsistencyResult(
                passed=True,
                greeting_name=cls.extract_greeting_name(draft_text),
                expected_name=None,
                violation=None,
            )

        greeting_name = cls.extract_greeting_name(draft_text)

        if greeting_name is None:
            # No greeting found — cannot check; pass to avoid false positives
            return NameConsistencyResult(
                passed=True,
                greeting_name=None,
                expected_name=expected_customer_name,
                violation=None,
            )

        if _names_match(greeting_name, expected_customer_name):
            return NameConsistencyResult(
                passed=True,
                greeting_name=greeting_name,
                expected_name=expected_customer_name,
                violation=None,
            )

        violation = (
            f"Draft greets '{greeting_name}' but the expected customer name is "
            f"'{expected_customer_name}'. A wrong customer name is a high-trust "
            "failure and must be corrected before sending."
        )
        return NameConsistencyResult(
            passed=False,
            greeting_name=greeting_name,
            expected_name=expected_customer_name,
            violation=violation,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _names_match(greeting_name: str, expected_name: str) -> bool:
    """Return True if greeting_name and expected_name are consistent.

    Rules (case-insensitive):
    1. Exact match: "Alice" == "Alice"
    2. True prefix: "Alex" matches "Alexander" (one is a prefix of the other)
    """
    a = greeting_name.strip().lower()
    b = expected_name.strip().lower()
    if a == b:
        return True
    # Allow one to be a leading-prefix of the other (e.g. Tom/Thomas)
    if a.startswith(b) or b.startswith(a):
        return True
    return False
