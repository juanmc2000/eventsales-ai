"""Tests for OccasionNormalisationService (ENQ-001).

All tests are unit-level — no DB or LLM required.
"""

from __future__ import annotations

import pytest

from app.modules.enquiries.occasion_normalisation_service import (
    ALL_CANONICAL_OCCASIONS,
    OCCASION_ANNIVERSARY,
    OCCASION_BABY_SHOWER,
    OCCASION_BIRTHDAY,
    OCCASION_CHRISTMAS,
    OCCASION_CORPORATE_EVENT,
    OCCASION_ENGAGEMENT_PARTY,
    OCCASION_GRADUATION,
    OCCASION_HEN_PARTY,
    OCCASION_OTHER,
    OCCASION_RETIREMENT,
    OCCASION_STAG_PARTY,
    OccasionNormalisationService,
)


@pytest.fixture()
def svc() -> OccasionNormalisationService:
    return OccasionNormalisationService()


# ── normalise() ────────────────────────────────────────────────────────────────


class TestNormalise:
    def test_none_returns_other(self, svc):
        assert svc.normalise(None) == OCCASION_OTHER

    def test_empty_string_returns_other(self, svc):
        assert svc.normalise("") == OCCASION_OTHER

    def test_whitespace_only_returns_other(self, svc):
        assert svc.normalise("   ") == OCCASION_OTHER

    def test_unknown_returns_other(self, svc):
        assert svc.normalise("private dining experience") == OCCASION_OTHER

    # Birthday
    @pytest.mark.parametrize("raw", [
        "birthday dinner",
        "birthday meal",
        "surprise birthday",
        "office birthday",
        "sister's birthday",
        "joint birthday party",
        "30th birthday",
        "Birthday Dinner",          # case-insensitive
    ])
    def test_birthday_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_BIRTHDAY

    # Anniversary
    @pytest.mark.parametrize("raw", [
        "anniversary dinner",
        "wedding anniversary",
        "10th anniversary",
    ])
    def test_anniversary_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_ANNIVERSARY

    # Engagement party
    @pytest.mark.parametrize("raw", [
        "engagement dinner",
        "engagement celebration",
        "engagement drinks",
        "engagement party",
    ])
    def test_engagement_party_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_ENGAGEMENT_PARTY

    # Baby shower
    @pytest.mark.parametrize("raw", [
        "baby shower",
        "babyshower",
        "baby-shower",
    ])
    def test_baby_shower_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_BABY_SHOWER

    # Hen party
    @pytest.mark.parametrize("raw", [
        "hen party",
        "hen do",
        "hen night",
        "bachelorette party",
    ])
    def test_hen_party_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_HEN_PARTY

    # Stag party
    @pytest.mark.parametrize("raw", [
        "stag party",
        "stag do",
        "stag night",
        "bachelor party",
    ])
    def test_stag_party_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_STAG_PARTY

    # Graduation
    @pytest.mark.parametrize("raw", [
        "graduation dinner",
        "graduating ceremony",
    ])
    def test_graduation_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_GRADUATION

    # Retirement
    @pytest.mark.parametrize("raw", [
        "retirement party",
        "retiring dinner",
        "farewell dinner",
        "leaving party",
        "leaving do",
    ])
    def test_retirement_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_RETIREMENT

    # Christmas
    @pytest.mark.parametrize("raw", [
        "christmas dinner",
        "xmas party",
        "festive meal",
        "holiday party",
    ])
    def test_christmas_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_CHRISTMAS

    # Corporate event
    @pytest.mark.parametrize("raw", [
        "team dinner",
        "client dinner",
        "networking event",
        "company celebration",
        "office party",
        "business dinner",
        "team lunch",
        "corporate event",
        "investor dinner",
    ])
    def test_corporate_event_variants(self, svc, raw):
        assert svc.normalise(raw) == OCCASION_CORPORATE_EVENT

    def test_result_always_in_canonical_set(self, svc):
        """Every possible normalise() result must be a known canonical value."""
        samples = [
            None, "", "birthday dinner", "client dinner",
            "random unknown occasion xyz", "baby shower",
        ]
        for raw in samples:
            result = svc.normalise(raw)
            assert result in ALL_CANONICAL_OCCASIONS, (
                f"normalise({raw!r}) returned {result!r} which is not in ALL_CANONICAL_OCCASIONS"
            )


# ── normalise_extraction() ────────────────────────────────────────────────────


class TestNormaliseExtraction:
    def test_none_input_returns_none(self, svc):
        assert svc.normalise_extraction(None) is None

    def test_empty_dict_returns_other(self, svc):
        result = svc.normalise_extraction({})
        assert result is not None
        assert result["occasion_canonical"] == OCCASION_OTHER

    def test_adds_occasion_canonical(self, svc):
        extracted = {"occasion": "birthday dinner", "guest_count": 10}
        result = svc.normalise_extraction(extracted)
        assert result["occasion_canonical"] == OCCASION_BIRTHDAY
        # Original field preserved
        assert result["occasion"] == "birthday dinner"
        # Other fields preserved
        assert result["guest_count"] == 10

    def test_does_not_mutate_input(self, svc):
        extracted = {"occasion": "engagement celebration"}
        original = dict(extracted)
        svc.normalise_extraction(extracted)
        assert extracted == original

    def test_null_occasion_maps_to_other(self, svc):
        result = svc.normalise_extraction({"occasion": None, "guest_count": 5})
        assert result["occasion_canonical"] == OCCASION_OTHER

    def test_unknown_occasion_maps_to_other(self, svc):
        result = svc.normalise_extraction({"occasion": "something unusual xyz"})
        assert result["occasion_canonical"] == OCCASION_OTHER

    def test_corporate_occasion_canonical(self, svc):
        result = svc.normalise_extraction({"occasion": "team dinner for 15 people"})
        assert result["occasion_canonical"] == OCCASION_CORPORATE_EVENT
