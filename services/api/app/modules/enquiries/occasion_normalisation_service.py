"""Occasion Normalisation Service (ENQ-001).

Maps free-text occasion values returned by the LLM into canonical occasion
identifiers used by downstream processing.

The LLM is responsible for identifying the occasion concept.
This service is responsible for normalising it deterministically.

Rules:
- Input (occasion_raw) is preserved unchanged alongside the canonical value.
- Matching is case-insensitive substring matching against keyword lists.
- Unknown/null occasions map to the canonical value ``other``.
- No LLM calls are made.
"""

from __future__ import annotations

# ── Canonical values ──────────────────────────────────────────────────────────

OCCASION_BIRTHDAY = "birthday"
OCCASION_ANNIVERSARY = "anniversary"
OCCASION_ENGAGEMENT_PARTY = "engagement_party"
OCCASION_BABY_SHOWER = "baby_shower"
OCCASION_HEN_PARTY = "hen_party"
OCCASION_STAG_PARTY = "stag_party"
OCCASION_GRADUATION = "graduation"
OCCASION_RETIREMENT = "retirement"
OCCASION_CHRISTMAS = "christmas"
OCCASION_CORPORATE_EVENT = "corporate_event"
OCCASION_OTHER = "other"

# All supported canonical values — used for validation in tests
ALL_CANONICAL_OCCASIONS = {
    OCCASION_BIRTHDAY,
    OCCASION_ANNIVERSARY,
    OCCASION_ENGAGEMENT_PARTY,
    OCCASION_BABY_SHOWER,
    OCCASION_HEN_PARTY,
    OCCASION_STAG_PARTY,
    OCCASION_GRADUATION,
    OCCASION_RETIREMENT,
    OCCASION_CHRISTMAS,
    OCCASION_CORPORATE_EVENT,
    OCCASION_OTHER,
}

# ── Keyword mapping ───────────────────────────────────────────────────────────
# Each entry is (canonical_value, list_of_keywords).
# Keywords are matched as case-insensitive substrings of the raw occasion string.
# Entries are checked in order — first match wins.

_MAPPING: list[tuple[str, list[str]]] = [
    (OCCASION_BIRTHDAY, [
        "birthday",
    ]),
    (OCCASION_ANNIVERSARY, [
        "anniversary",
    ]),
    (OCCASION_ENGAGEMENT_PARTY, [
        "engagement",
    ]),
    (OCCASION_BABY_SHOWER, [
        "baby shower",
        "babyshower",
        "baby-shower",
        "baby_shower",
    ]),
    (OCCASION_HEN_PARTY, [
        "hen party",
        "hen do",
        "hen night",
        "bachelorette",
    ]),
    (OCCASION_STAG_PARTY, [
        "stag party",
        "stag do",
        "stag night",
        "bachelor party",
    ]),
    (OCCASION_GRADUATION, [
        "graduation",
        "graduating",
    ]),
    (OCCASION_RETIREMENT, [
        "retirement",
        "retiring",
        "farewell",
        "leaving party",
        "leaving do",
    ]),
    (OCCASION_CHRISTMAS, [
        "christmas",
        "xmas",
        "festive",
        "holiday party",
    ]),
    (OCCASION_CORPORATE_EVENT, [
        "corporate",
        "team dinner",
        "client dinner",
        "client lunch",
        "networking",
        "company celebration",
        "office party",
        "office dinner",
        "office lunch",
        "business dinner",
        "business lunch",
        "work dinner",
        "work lunch",
        "team lunch",
        "team event",
        "company dinner",
        "company lunch",
        "board dinner",
        "board lunch",
        "investor",
    ]),
]


# ── Service ───────────────────────────────────────────────────────────────────


class OccasionNormalisationService:
    """Normalise a free-text occasion string to a canonical value.

    Usage::

        svc = OccasionNormalisationService()
        canonical = svc.normalise("surprise birthday dinner for my sister")
        # → "birthday"
    """

    def normalise(self, occasion_raw: str | None) -> str:
        """Return the canonical occasion for the given raw string.

        Returns ``"other"`` when the input is None, empty, or does not match
        any known keyword.

        Args:
            occasion_raw: Free-text occasion as returned by the LLM.

        Returns:
            A canonical occasion string from ``ALL_CANONICAL_OCCASIONS``.
        """
        if not occasion_raw or not occasion_raw.strip():
            return OCCASION_OTHER

        lower = occasion_raw.lower()

        for canonical, keywords in _MAPPING:
            for kw in keywords:
                if kw in lower:
                    return canonical

        return OCCASION_OTHER

    def normalise_extraction(self, extracted_json: dict | None) -> dict | None:
        """Apply occasion normalisation to an extracted JSON dict.

        Adds ``occasion_canonical`` alongside the existing ``occasion`` field.
        Returns a new dict — does not mutate the input.

        Args:
            extracted_json: The parsed extraction dict from the LLM.

        Returns:
            A copy of ``extracted_json`` with ``occasion_canonical`` added,
            or ``None`` if ``extracted_json`` is ``None``.
        """
        if extracted_json is None:
            return extracted_json

        result = dict(extracted_json)
        occasion_raw: str | None = result.get("occasion")
        result["occasion_canonical"] = self.normalise(occasion_raw)
        return result
