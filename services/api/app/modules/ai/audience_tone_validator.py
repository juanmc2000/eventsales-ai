"""Audience Tone Validator (RESP-075).

Validates that a generated draft response uses audience-appropriate language.

Scope:
  - corporate: professional, polished, efficient — no social celebration warmth
  - agency: operational, clear — no emotional celebration language
  - luxury: refined, understated — no casual or over-enthusiastic phrasing
  - social: warm and celebratory language is explicitly allowed
  - unknown: no tone restrictions enforced (neutral fallback acceptable)

The validator is deterministic — no LLM calls are made.

Violations are labelled with the code ``audience_tone_violation`` so downstream
consumers (auto-send policy, compliance reporting) can identify them distinctly
from factual compliance violations.

Usage::

    from app.modules.ai.audience_tone_validator import AudienceToneValidator

    result = AudienceToneValidator.validate(
        draft="How wonderful — a board dinner is such an important occasion.",
        audience_type="corporate",
    )
    # result.passed → False
    # result.violations[0] → "audience_tone_violation: corporate — 'How wonderful' detected"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Forbidden pattern definitions ─────────────────────────────────────────────

# Social warmth patterns that are inappropriate in corporate / agency responses.
# These are phrases that treat a business booking as a personal celebration.
_CORPORATE_AGENCY_FORBIDDEN: list[tuple[str, re.Pattern[str]]] = [
    ("how wonderful",        re.compile(r"\bhow\s+wonderful\b",              re.IGNORECASE)),
    ("how lovely",           re.compile(r"\bhow\s+lovely\b",                 re.IGNORECASE)),
    ("such a special occasion", re.compile(r"\bsuch\s+a\s+special\s+occasion\b", re.IGNORECASE)),
    ("such a meaningful occasion", re.compile(r"\bsuch\s+a\s+meaningful\s+occasion\b", re.IGNORECASE)),
    ("celebration with us",  re.compile(r"\bcelebration\s+with\s+us\b",      re.IGNORECASE)),
    ("will be special",      re.compile(r"\bwill\s+be\s+special\b",          re.IGNORECASE)),
    ("what a lovely occasion", re.compile(r"\bwhat\s+a\s+lovely\s+occasion\b", re.IGNORECASE)),
    ("how exciting",         re.compile(r"\bhow\s+exciting\b",               re.IGNORECASE)),
    ("how delightful",       re.compile(r"\bhow\s+delightful\b",             re.IGNORECASE)),
    ("what a wonderful",     re.compile(r"\bwhat\s+a\s+wonderful\b",         re.IGNORECASE)),
    ("delighted to celebrate", re.compile(r"\bdelighted\s+to\s+celebrate\b", re.IGNORECASE)),
    ("thrilled",             re.compile(r"\bthrilled\b",                     re.IGNORECASE)),
]

# Casual / enthusiastic patterns inappropriate for luxury clients.
# Luxury tone should be refined and understated — not consumer-enthusiastic.
_LUXURY_FORBIDDEN: list[tuple[str, re.Pattern[str]]] = [
    ("amazing",   re.compile(r"\bamazing\b",   re.IGNORECASE)),
    ("fantastic", re.compile(r"\bfantastic\b", re.IGNORECASE)),
    ("brilliant", re.compile(r"\bbrilliant\b", re.IGNORECASE)),
    ("super",     re.compile(r"\bsuper\b",     re.IGNORECASE)),
    ("totally",   re.compile(r"\btotally\b",   re.IGNORECASE)),
    ("can't wait", re.compile(r"can'?t\s+wait", re.IGNORECASE)),
    ("how exciting", re.compile(r"\bhow\s+exciting\b", re.IGNORECASE)),
]

# Map audience_type → list of (label, pattern) pairs to check.
_RULES: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "corporate": _CORPORATE_AGENCY_FORBIDDEN,
    "agency":    _CORPORATE_AGENCY_FORBIDDEN,
    "luxury":    _LUXURY_FORBIDDEN,
    "social":    [],   # social allows celebratory language — no restrictions
    "unknown":   [],   # unknown: no tone restrictions enforced
}


# ── Result ────────────────────────────────────────────────────────────────────


@dataclass
class ToneValidationResult:
    """Result of AudienceToneValidator.validate().

    Attributes:
        passed:       True when no tone violations were found.
        violations:   List of violation strings, each prefixed with
                      ``audience_tone_violation:``.
        audience_type: The audience_type the validation was run against.
    """

    passed: bool
    audience_type: str
    violations: list[str] = field(default_factory=list)


# ── Validator ─────────────────────────────────────────────────────────────────


class AudienceToneValidator:
    """Deterministic audience-aware draft tone validator.

    Checks a generated draft for language that is inappropriate for the
    given audience type.  No LLM calls are made.

    Corporate and agency responses must not use emotional celebration language.
    Luxury responses must not use casual or over-enthusiastic phrasing.
    Social and unknown responses are not restricted.
    """

    @classmethod
    def validate(cls, draft: str, audience_type: str) -> ToneValidationResult:
        """Validate ``draft`` tone for ``audience_type``.

        Args:
            draft:         The generated draft text (post-processed, not raw LLM).
            audience_type: One of corporate, agency, luxury, social, unknown.
                           Unrecognised values are treated as unknown (no restrictions).

        Returns:
            ToneValidationResult with passed=True when no violations are found.
        """
        aud = (audience_type or "").lower().strip()
        rules = _RULES.get(aud, [])   # unknown types → no rules

        if not rules:
            return ToneValidationResult(passed=True, audience_type=aud)

        violations: list[str] = []
        draft_text = draft or ""

        for label, pattern in rules:
            if pattern.search(draft_text):
                violations.append(
                    f"audience_tone_violation: {aud} — '{label}' detected"
                )

        return ToneValidationResult(
            passed=len(violations) == 0,
            audience_type=aud,
            violations=violations,
        )
