"""Auto-Send Eligibility Policy V1 (AUTO-001).

Defines the canonical set of rules governing which first-response scenarios
may be auto-sent without human review.

Design rules:
- All auto-send decisions are deterministic — no LLM calls are made.
- The policy prefers false negatives over false positives.  When in doubt,
  require human review.
- Every rule is explicitly stated so the policy is auditable.

Auto-send ALLOWED only when ALL of the following are true:

  1. Response goal is in ALLOWED_GOALS
     (CONFIRM_AVAILABLE, ACKNOWLEDGE_AND_CHECK_AVAILABILITY, or
     REQUEST_DATE_CONFIRMATION).
  2. Date status is in ALLOWED_DATE_STATUSES
     (resolved, resolved_with_confirmation, or pending_date_confirmation).
  3. Draft compliance passed (DraftComplianceValidator returned passed=True).
  4. Context integrity gate passed.

Auto-send BLOCKED for:

  - RESPOND_UNAVAILABLE — unavailable responses require human review before
    sending to avoid communicating incorrect refusals.
  - REQUEST_WEBFORM — sending a webform redirect without review may be
    confusing for guests who provided detailed information.
  - ESCALATE_TO_HUMAN — the system has flagged this for human handling.
  - REQUEST_MISSING_INFORMATION — automatically requesting information may
    ask for details the guest has already provided elsewhere.
  - ambiguous / unknown date status — date must be deterministically resolved
    before auto-sending.
  - context mismatch — availability context does not match the prompt context.
  - draft compliance failure — validator detected a hallucination or policy
    violation in the draft.

Note on REQUEST_DATE_CONFIRMATION (HOTFIX-007):

  After RESP-073, RDTC responses are fully deterministic copy-block assembly
  (BLOCK_RDTC_AVAILABLE_OPENER + BLOCK_RDTC_NEXT_STEP).  There is no LLM call,
  no invented questions, and no hallucination risk.  The date ambiguity is
  communicated to the guest in the response — that is the entire purpose of
  the message — so human review before sending provides no additional safety.

Usage::

    from app.modules.ai.auto_send_policy import AutoSendEligibilityPolicy

    # Check whether a goal is eligible
    eligible = AutoSendEligibilityPolicy.is_goal_eligible("CONFIRM_AVAILABLE")  # True
    eligible = AutoSendEligibilityPolicy.is_goal_eligible("RESPOND_UNAVAILABLE")  # False

    # Check whether a date status permits auto-send
    ok = AutoSendEligibilityPolicy.is_date_status_eligible("resolved")  # True
    ok = AutoSendEligibilityPolicy.is_date_status_eligible("ambiguous")  # False

    # Get a policy summary
    summary = AutoSendEligibilityPolicy.policy_summary()
"""

from __future__ import annotations

from typing import Any

# ── Policy constants ────────────────────────────────────────────────────────────

# Goals that may be auto-sent (allowlist — all others require human review)
ALLOWED_GOALS: frozenset[str] = frozenset({
    "CONFIRM_AVAILABLE",
    "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
    # HOTFIX-007: RDTC is fully deterministic copy-block assembly after RESP-073;
    # no LLM, no invented questions — safe to auto-send.
    "REQUEST_DATE_CONFIRMATION",
})

# Goals that explicitly require human review (documented for auditability)
BLOCKED_GOALS: frozenset[str] = frozenset({
    "RESPOND_UNAVAILABLE",
    "REQUEST_MISSING_INFORMATION",
    "REQUEST_WEBFORM",
    "ESCALATE_TO_HUMAN",
})

# Date resolution statuses that permit auto-send (allowlist — all others block)
ALLOWED_DATE_STATUSES: frozenset[str] = frozenset({
    "resolved",
    "resolved_with_confirmation",
    # HOTFIX-007: RDTC emails carry pending_date_confirmation — the ambiguity
    # is surfaced to the guest in the deterministic copy block, so this status
    # is safe for auto-send.
    "pending_date_confirmation",
})

# Date statuses that require human review
BLOCKED_DATE_STATUSES: frozenset[str] = frozenset({
    "ambiguous",
    "unknown",
    "unresolved",
})

# Policy version for traceability
POLICY_VERSION = "1.0"


# ── Policy class ─────────────────────────────────────────────────────────────────


class AutoSendEligibilityPolicy:
    """V1 auto-send eligibility policy — declarative rule set.

    This class defines WHAT is allowed/blocked.
    The AutoSendReadinessGate evaluates a specific draft against these rules.
    """

    #: Goals that may be auto-sent.
    ALLOWED_GOALS: frozenset[str] = ALLOWED_GOALS

    #: Goals that must always go through human review before sending.
    BLOCKED_GOALS: frozenset[str] = BLOCKED_GOALS

    #: Date resolution statuses that permit auto-send.
    ALLOWED_DATE_STATUSES: frozenset[str] = ALLOWED_DATE_STATUSES

    #: Date statuses that block auto-send.
    BLOCKED_DATE_STATUSES: frozenset[str] = BLOCKED_DATE_STATUSES

    #: Policy version string for traceability.
    VERSION: str = POLICY_VERSION

    @classmethod
    def is_goal_eligible(cls, response_goal: str) -> bool:
        """Return True if the response goal is eligible for auto-send.

        Goals not in ALLOWED_GOALS are always blocked, regardless of other conditions.
        """
        return response_goal in cls.ALLOWED_GOALS

    @classmethod
    def is_date_status_eligible(cls, date_status: str) -> bool:
        """Return True if the date resolution status permits auto-send.

        Only 'resolved' and 'resolved_with_confirmation' are permitted.
        Any other value (including None, empty string, 'ambiguous') blocks auto-send.
        """
        return date_status in cls.ALLOWED_DATE_STATUSES

    @classmethod
    def goal_block_reason(cls, response_goal: str) -> str | None:
        """Return a human-readable reason why a goal is blocked, or None if allowed.

        Used by AutoSendReadinessGate to produce consistent blocker messages.
        """
        if response_goal in cls.ALLOWED_GOALS:
            return None
        reasons: dict[str, str] = {
            "RESPOND_UNAVAILABLE": (
                "Unavailable responses require human review before sending "
                "to avoid communicating incorrect refusals."
            ),
            "REQUEST_MISSING_INFORMATION": (
                "Automatically requesting information may ask for details the "
                "guest has already provided elsewhere."
            ),
            "REQUEST_WEBFORM": (
                "Sending a webform redirect without review may be confusing "
                "for guests who provided detailed information."
            ),
            "ESCALATE_TO_HUMAN": (
                "The system has flagged this enquiry for human handling."
            ),
        }
        base = reasons.get(response_goal)
        allowed_set = ", ".join(sorted(cls.ALLOWED_GOALS))
        if base:
            return (
                f"Response goal '{response_goal}' is not in the auto-send allowed set "
                f"({allowed_set}). {base}"
            )
        return (
            f"Response goal '{response_goal}' is not in the auto-send allowed set "
            f"({allowed_set})."
        )

    @classmethod
    def date_status_block_reason(cls, date_status: str) -> str | None:
        """Return a human-readable reason why a date status is blocked, or None if allowed."""
        if date_status in cls.ALLOWED_DATE_STATUSES:
            return None
        return (
            f"Date status '{date_status}' requires human review — "
            "auto-send requires 'resolved' or 'resolved_with_confirmation'."
        )

    @classmethod
    def policy_summary(cls) -> dict[str, Any]:
        """Return a structured summary of the policy rules for display/logging."""
        return {
            "policy_version": cls.VERSION,
            "allowed_goals": sorted(cls.ALLOWED_GOALS),
            "blocked_goals": sorted(cls.BLOCKED_GOALS),
            "allowed_date_statuses": sorted(cls.ALLOWED_DATE_STATUSES),
            "blocked_date_statuses": sorted(cls.BLOCKED_DATE_STATUSES),
            "additional_requirements": [
                "Draft compliance must pass (DraftComplianceValidator)",
                "Context integrity gate must pass (ResponseContextIntegrityGate)",
            ],
        }
