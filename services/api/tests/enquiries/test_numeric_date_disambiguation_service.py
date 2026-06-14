"""Tests for NumericDateDisambiguationService (HOTFIX-001).

All tests are pure-Python unit tests — no DB, no LLM.
Anchor date used throughout unless stated: 2026-06-03 (Wednesday).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.enquiries.numeric_date_disambiguation_service import (
    AMERICAN_NEAR_DAYS,
    BRITISH_FAR_DAYS,
    CLOSE_CALL_DAYS,
    NEAR_HORIZON_DAYS,
    RESOLVED,
    RESOLVED_WITH_CONFIRMATION,
    UNRESOLVED_AMBIGUITY,
    DisambiguationResult,
    NumericDateDisambiguationService,
)

ANCHOR = date(2026, 6, 3)  # Wednesday


# ── Rule 1 — Unambiguous dates ─────────────────────────────────────────────────


class TestRule1UnambiguousDates:
    """When one value > 12 there is only one valid interpretation."""

    def test_25_7_is_dd_mm_july_25(self) -> None:
        r = NumericDateDisambiguationService.disambiguate(25, 7, ANCHOR)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 7, 25)
        assert r.alternative_date is None
        assert r.clarification_required is False

    def test_18_3_is_dd_mm_march_18(self) -> None:
        r = NumericDateDisambiguationService.disambiguate(18, 3, ANCHOR)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 3, 18) or r.assumed_date == date(2027, 3, 18)
        # March 18 2026 is in the past from anchor Jun 3 2026 → rolls to 2027
        assert r.assumed_date == date(2027, 3, 18)
        assert r.clarification_required is False

    def test_13_10_is_dd_mm_october_13(self) -> None:
        r = NumericDateDisambiguationService.disambiguate(13, 10, ANCHOR)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 10, 13)
        assert r.clarification_required is False

    def test_value2_gt_12_resolves_as_mm_dd(self) -> None:
        # "7/25" → DD must be 25, month must be 7 (July)
        r = NumericDateDisambiguationService.disambiguate(7, 25, ANCHOR)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 7, 25)
        assert r.clarification_required is False

    def test_unambiguous_rolls_to_next_year_when_past(self) -> None:
        # 25/2 (Feb 25) is in the past from June anchor → rolls to 2027
        r = NumericDateDisambiguationService.disambiguate(25, 2, ANCHOR)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2027, 2, 25)
        assert r.clarification_required is False


# ── Rule 3 + default behaviour ─────────────────────────────────────────────────


class TestRule3BritishDefault:
    """DD/MM is the default when both values ≤ 12 and no heuristic overrides."""

    def test_british_interpretation_is_default(self) -> None:
        # "1/9" → british DD=1 MM=9 → Sep 1 2026 (90 days), american MM=1 DD=9 → Jan 9 2027 (220+ days)
        r = NumericDateDisambiguationService.disambiguate(1, 9, ANCHOR)
        assert r.assumed_date == date(2026, 9, 1)

    def test_british_date_is_near_american_is_far(self) -> None:
        # "3/8" → british Aug 3 (61 days ≤ 120), american Mar 8 2026 past → Mar 8 2027 (278 days > 120)
        # HOTFIX-008 Rule 4: British is near, American is far → resolved directly, no clarification
        r = NumericDateDisambiguationService.disambiguate(3, 8, ANCHOR)
        assert r.assumed_date == date(2026, 8, 3)
        assert r.ambiguity_type == RESOLVED
        assert r.clarification_required is False
        assert r.alternative_date is None


# ── Rule 4 — Near-horizon resolution (HOTFIX-008) ─────────────────────────────


class TestRule4NearHorizon:
    """If one interpretation is within NEAR_HORIZON_DAYS and the other is beyond
    it, resolve directly to the nearer date without clarification."""

    def test_6_7_british_near_resolves_directly(self) -> None:
        # "6/7" on Jun 14: british Jul 6 2026 (22d ≤ 120), american Jun 7 2026 past → Jun 7 2027 (358d)
        anchor = date(2026, 6, 14)
        r = NumericDateDisambiguationService.disambiguate(6, 7, anchor)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 7, 6)
        assert r.alternative_date is None
        assert r.clarification_required is False

    def test_7_6_american_near_resolves_directly(self) -> None:
        # "7/6" on Jun 14: british Jun 7 2026 past → Jun 7 2027 (358d), american Jul 6 2026 (22d ≤ 120)
        anchor = date(2026, 6, 14)
        r = NumericDateDisambiguationService.disambiguate(7, 6, anchor)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 7, 6)
        assert r.alternative_date is None
        assert r.clarification_required is False

    def test_both_within_horizon_does_not_trigger_rule_4(self) -> None:
        # "9/8" on Jun 14: british Aug 9 2026 (56d), american Sep 8 2026 (86d) — both ≤ 120
        anchor = date(2026, 6, 14)
        r = NumericDateDisambiguationService.disambiguate(9, 8, anchor)
        assert r.ambiguity_type != RESOLVED  # Rule 4 does not apply

    def test_both_beyond_horizon_does_not_trigger_rule_4(self) -> None:
        # "1/3" on Jun 3: british Mar 1 2027 (271d), american Jan 3 2027 (214d) — both > 120
        r = NumericDateDisambiguationService.disambiguate(1, 3, ANCHOR)
        # Rule 4 does not apply; falls through to Rule 6 (next year)
        assert r.clarification_required is True

    def test_near_horizon_boundary_at_exactly_120_days(self) -> None:
        # A date exactly 120 days from anchor should be treated as "near"
        anchor = date(2026, 6, 3)
        # anchor + 120 = 2026-10-01 → Oct 1 is day=1, month=10
        # "1/10" → british Oct 1 2026 (120d ≤ 120 = near), american Jan 10 2027 (221d > 120 = far)
        r = NumericDateDisambiguationService.disambiguate(1, 10, anchor)
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 10, 1)
        assert r.clarification_required is False


# ── Rule 5 — Horizon heuristic ────────────────────────────────────────────────


class TestRule5HorizonHeuristic:
    """If British > 180 days and American ≤ 90 days, prefer American."""

    def test_9_1_american_preferred_by_rule_4(self) -> None:
        # "9/1" → british Jan 9 2027 (~220 days > 120), american Sep 1 2026 (90 days ≤ 120)
        # HOTFIX-008 Rule 4: American is near, British is far → resolved directly, no clarification
        r = NumericDateDisambiguationService.disambiguate(9, 1, ANCHOR)
        assert r.assumed_date == date(2026, 9, 1)
        assert r.alternative_date is None
        assert r.ambiguity_type == RESOLVED
        assert r.clarification_required is False

    def test_rule5_not_triggered_when_british_within_180(self) -> None:
        # british date within 180 days → Rule 5 does not apply
        # "1/9" → british Sep 1 2026 (90 days), american Jan 9 2027 (220 days)
        r = NumericDateDisambiguationService.disambiguate(1, 9, ANCHOR)
        assert r.clarification_reason != "american_nearer_by_horizon_heuristic"
        assert r.assumed_date == date(2026, 9, 1)  # british still chosen (default)

    def test_rule5_not_triggered_when_american_beyond_near_threshold(self) -> None:
        # american just beyond 90 days → Rule 5 should NOT fire
        # Use anchor 2026-09-01, "9/1" → british Jan 9 (130 days past next year?), american Sep 1 past
        # Construct a case: anchor 2026-01-01, "12/1" → british Jan 12 (11 days), american Dec 1 (334 days)
        anchor = date(2026, 1, 1)
        r = NumericDateDisambiguationService.disambiguate(12, 1, anchor)
        # british Jan 12 2026 (11 days), american Dec 1 2026 (334 days)
        # british NOT > 180, so Rule 5 doesn't apply
        assert r.clarification_reason != "american_nearer_by_horizon_heuristic"
        assert r.assumed_date == date(2026, 1, 12)


# ── Rule 6 — Next-year protection ─────────────────────────────────────────────


class TestRule6NextYearProtection:
    """If assumed date is in next calendar year and today is not Oct/Nov/Dec."""

    def test_next_year_assumption_outside_q4_requires_confirmation(self) -> None:
        # anchor = June 3 (not Q4); "1/2" → british Feb 1 2026 past → Feb 1 2027 (next year)
        # american = Jan 2 → past → Jan 2 2027 (also next year but different dates)
        r = NumericDateDisambiguationService.disambiguate(1, 2, ANCHOR)
        # british = Feb 1 2027, american = Jan 2 2027
        # Rule 5: british days ~243, american days ~213 — neither triggers Rule 5
        # Rule 6: british (assumed) is in next year + anchor is June → flag
        assert r.clarification_required is True
        assert r.clarification_reason == "next_year_assumption"

    def test_next_year_assumption_in_q4_is_allowed(self) -> None:
        # anchor = November 15 — Q4, next-year dates are expected
        anchor_q4 = date(2026, 11, 15)
        # "1/2" → british Feb 1 2027 (next year), american Jan 2 2027 (next year)
        r = NumericDateDisambiguationService.disambiguate(1, 2, anchor_q4)
        # Rule 6 does NOT fire since anchor is in November (Q4)
        assert r.clarification_reason != "next_year_assumption"

    def test_rule6_not_triggered_when_assumed_date_in_current_year(self) -> None:
        # "1/9" → british Sep 1 2026 (same year) → Rule 6 should NOT fire
        r = NumericDateDisambiguationService.disambiguate(1, 9, ANCHOR)
        assert r.clarification_reason != "next_year_assumption"


# ── Rule 7 — Unresolved ambiguity ─────────────────────────────────────────────


class TestRule7UnresolvedAmbiguity:
    """When both interpretations are too close to call."""

    def test_7_6_close_call_is_unresolved(self) -> None:
        # anchor 2026-06-03; "7/6" → british Jun 7 (4 days), american Jul 6 (33 days)
        # |4 - 33| = 29 ≤ CLOSE_CALL_DAYS → unresolved
        r = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        assert r.ambiguity_type == UNRESOLVED_AMBIGUITY
        assert r.assumed_date == date(2026, 6, 7)  # British fallback
        assert r.alternative_date == date(2026, 7, 6)
        assert r.clarification_required is True

    def test_assumed_date_is_british_fallback_for_unresolved(self) -> None:
        r = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        # Even when unresolved, British default is the assumed date
        assert r.assumed_date == date(2026, 6, 7)

    def test_clearly_separated_dates_not_unresolved(self) -> None:
        # "9/1" → british 220 days, american 90 days → Rule 4 applies (American near), not Rule 7
        r = NumericDateDisambiguationService.disambiguate(9, 1, ANCHOR)
        assert r.ambiguity_type != UNRESOLVED_AMBIGUITY


# ── from_raw_text ──────────────────────────────────────────────────────────────


class TestFromRawText:
    """Parse raw text strings like '7/6' before disambiguating."""

    def test_parses_standard_slash_format(self) -> None:
        r = NumericDateDisambiguationService.from_raw_text("9/1", ANCHOR)
        assert r is not None
        assert r.assumed_date == date(2026, 9, 1)

    def test_parses_with_spaces_around_slash(self) -> None:
        r = NumericDateDisambiguationService.from_raw_text("9 / 1", ANCHOR)
        assert r is not None
        assert r.assumed_date == date(2026, 9, 1)

    def test_returns_none_for_non_numeric(self) -> None:
        assert NumericDateDisambiguationService.from_raw_text("next Friday", ANCHOR) is None

    def test_returns_none_for_iso_date(self) -> None:
        assert NumericDateDisambiguationService.from_raw_text("2026-09-01", ANCHOR) is None

    def test_returns_none_for_none_input(self) -> None:
        assert NumericDateDisambiguationService.from_raw_text(None, ANCHOR) is None

    def test_returns_none_for_empty_string(self) -> None:
        assert NumericDateDisambiguationService.from_raw_text("", ANCHOR) is None

    def test_parses_25_7_as_unambiguous(self) -> None:
        r = NumericDateDisambiguationService.from_raw_text("25/7", ANCHOR)
        assert r is not None
        assert r.ambiguity_type == RESOLVED
        assert r.assumed_date == date(2026, 7, 25)

    def test_raw_text_with_leading_text_not_parsed(self) -> None:
        # "on 7/6" — has a prefix, regex won't match
        assert NumericDateDisambiguationService.from_raw_text("on 7/6", ANCHOR) is None


# ── Clarification question text ───────────────────────────────────────────────


class TestClarificationQuestion:
    """Clarification questions are generated for all non-resolved cases."""

    def test_resolved_has_no_clarification_question(self) -> None:
        r = NumericDateDisambiguationService.disambiguate(25, 7, ANCHOR)
        assert r.clarification_question is None

    def test_resolved_with_confirmation_includes_provisional_text(self) -> None:
        # Use a next-year ambiguity case (Rule 6) which still generates resolved_with_confirmation:
        # "3/1" with anchor 2026-06-03 → british Jan 3 2027 (214d), american Mar 1 2027 (271d)
        # Both > 120d so Rule 4 doesn't apply; Rule 6 fires (next year, not Q4)
        r = NumericDateDisambiguationService.disambiguate(3, 1, ANCHOR)
        assert r.ambiguity_type == RESOLVED_WITH_CONFIRMATION
        assert "provisionally" in (r.clarification_question or "").lower()

    def test_unresolved_ambiguity_question_mentions_both_dates(self) -> None:
        r = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        q = r.clarification_question or ""
        assert "June" in q and "July" in q


# ── Integration with DateResolutionResult ─────────────────────────────────────


class TestDisambiguationInResolver:
    """Smoke test: disambiguation fields appear in DateResolutionResult."""

    def test_ambiguous_type_triggers_disambiguation_in_resolver(self) -> None:
        import uuid
        from unittest.mock import patch
        from app.modules.enquiries.date_resolution_service import (
            DateResolutionRequest,
            EnquiryDateResolutionService,
        )
        from unittest.mock import MagicMock

        service = EnquiryDateResolutionService(db=MagicMock())
        request = DateResolutionRequest(
            enquiry_id=uuid.uuid4(),
            date_request_dict={
                "date_request_type": "ambiguous_numeric_date",
                "raw_text": "9/1",
                "anchor_date": "2026-06-03",
                "requires_date_clarification": True,
                "ambiguous_dates": [{"possible_dates": ["2026-01-09", "2026-09-01"]}],
            },
            anchor_date_override=ANCHOR,
        )
        with (
            patch.object(service, "_persist_date_request", return_value=None),
            patch.object(service, "_persist_candidate_dates"),
        ):
            result = service.resolve(request)

        # HOTFIX-008 Rule 4: Sep 1 (90d ≤ 120) is near, Jan 9 2027 (220d > 120) is far
        # → resolved directly with no clarification required
        assert result.assumed_date == date(2026, 9, 1)
        assert result.candidate_dates == [date(2026, 9, 1)]
        assert result.ambiguity_type == RESOLVED
        assert result.ambiguity_clarification_required is False

    def test_non_ambiguous_type_has_no_disambiguation_fields(self) -> None:
        import uuid
        from unittest.mock import patch
        from app.modules.enquiries.date_resolution_service import (
            DateResolutionRequest,
            EnquiryDateResolutionService,
        )
        from unittest.mock import MagicMock

        service = EnquiryDateResolutionService(db=MagicMock())
        request = DateResolutionRequest(
            enquiry_id=uuid.uuid4(),
            date_request_dict={
                "date_request_type": "exact",
                "explicit_dates": ["2026-08-15"],
            },
            anchor_date_override=ANCHOR,
        )
        with (
            patch.object(service, "_persist_date_request", return_value=None),
            patch.object(service, "_persist_candidate_dates"),
        ):
            result = service.resolve(request)

        assert result.ambiguity_type is None
        assert result.assumed_date is None
        assert result.ambiguity_clarification_required is False
