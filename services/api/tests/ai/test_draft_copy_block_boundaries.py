"""Tests for RESP-034 — approved copy block boundary enforcement.

Validates that extra text appended after approved copy blocks is detected,
especially when the extra text discusses forbidden topics.
"""

from __future__ import annotations

import pytest

from app.modules.ai.draft_compliance_validator import (
    DraftComplianceValidator,
    ValidationContext,
    ViolationDetail,
)
from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary


# ── Fixtures ──────────────────────────────────────────────────────────────────

AVAIL_CONFIRMED = FirstResponseCopyLibrary.render(
    "availability_confirmed", {"meal_period": "dinner", "event_date": "12th June"}
)
AVAIL_NOT_CHECKED = FirstResponseCopyLibrary.render(
    "availability_not_checked", {"meal_period": "dinner", "event_date": "12th June"}
)
NEXT_STEP_BOOKING = FirstResponseCopyLibrary.render("booking_next_step")
NEXT_STEP_CHECK = FirstResponseCopyLibrary.render("availability_check_next_step")
SIGNOFF = FirstResponseCopyLibrary.render("signoff", {"persona_name": "Eleanor"})


def _ctx(approved_blocks: list[str], **kwargs) -> ValidationContext:
    defaults = dict(
        availability_contract="CONFIRMED_AVAILABLE",
        response_goal="CONFIRM_AVAILABLE",
    )
    defaults.update(kwargs)
    return ValidationContext(approved_blocks=approved_blocks, **defaults)


def _validate(draft: str, approved_blocks: list[str], **kwargs):
    return DraftComplianceValidator.validate(draft, _ctx(approved_blocks, **kwargs))


# ── No extension — exact blocks pass ─────────────────────────────────────────


class TestExactBlocksPasses:
    def test_exact_confirmed_block_passes(self) -> None:
        draft = f"Dear Alice,\n\n{AVAIL_CONFIRMED}\n\n{SIGNOFF}"
        result = _validate(draft, approved_blocks=[AVAIL_CONFIRMED, SIGNOFF])
        ext_violations = [v for v in result.violations if "copy_block_post_extension" in v or "extends an approved" in v.lower()]
        assert ext_violations == []

    def test_exact_next_step_plus_signoff_passes(self) -> None:
        draft = f"Dear Alice,\n\n{AVAIL_CONFIRMED}\n\n{NEXT_STEP_BOOKING}\n\n{SIGNOFF}"
        result = _validate(draft, approved_blocks=[AVAIL_CONFIRMED, NEXT_STEP_BOOKING, SIGNOFF])
        ext_violations = [v for v in result.violations if "extends an approved" in v.lower()]
        assert ext_violations == []

    def test_no_approved_blocks_skips_check(self) -> None:
        result = _validate(
            "Dear Alice, thank you.",
            approved_blocks=[],
        )
        assert result.passed is True


# ── Post-block extension with forbidden topic — fail ─────────────────────────


class TestPostBlockExtensionForbiddenTopics:
    def test_menu_extension_after_confirmed_block_fails(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_CONFIRMED} We can also discuss menu options at your convenience. "
            f"\n\n{SIGNOFF}"
        )
        result = _validate(draft, approved_blocks=[AVAIL_CONFIRMED, SIGNOFF])
        ext_violations = [v for v in result.violations if "extends an approved" in v.lower()]
        assert len(ext_violations) >= 1

    def test_extension_in_structured_violations(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_CONFIRMED} We can also discuss menu options for the evening. "
            f"\n\n{SIGNOFF}"
        )
        result = _validate(draft, approved_blocks=[AVAIL_CONFIRMED, SIGNOFF])
        sv = [v for v in result.structured_violations if v.code == "copy_block_post_extension"]
        assert sv
        assert sv[0].severity == "high"
        assert sv[0].matched_text != ""

    def test_special_touches_extension_fails(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_CONFIRMED} We can arrange special touches to personalise your evening. "
            f"\n\n{SIGNOFF}"
        )
        result = _validate(draft, approved_blocks=[AVAIL_CONFIRMED, SIGNOFF])
        ext_violations = [v for v in result.violations if "extends an approved" in v.lower()]
        assert ext_violations

    def test_dietary_extension_after_next_step_fails(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_CONFIRMED}\n\n"
            f"{NEXT_STEP_BOOKING} We are happy to accommodate dietary requirements. "
            f"\n\n{SIGNOFF}"
        )
        result = _validate(draft, approved_blocks=[AVAIL_CONFIRMED, NEXT_STEP_BOOKING, SIGNOFF])
        ext_violations = [v for v in result.violations if "extends an approved" in v.lower()]
        assert ext_violations

    def test_timing_extension_fails(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_NOT_CHECKED} We can discuss your preferred timing when we follow up. "
            f"\n\n{SIGNOFF}"
        )
        result = _validate(
            draft,
            approved_blocks=[AVAIL_NOT_CHECKED, SIGNOFF],
            availability_contract="NOT_CHECKED",
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        )
        ext_violations = [v for v in result.violations if "extends an approved" in v.lower()]
        assert ext_violations


# ── Acceptance criteria coverage ─────────────────────────────────────────────


class TestAcceptanceCriteria:
    def test_confirm_available_goal_covered(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_CONFIRMED} We can discuss menu options at your convenience.\n\n{SIGNOFF}"
        )
        result = _validate(
            draft,
            approved_blocks=[AVAIL_CONFIRMED, SIGNOFF],
            availability_contract="CONFIRMED_AVAILABLE",
            response_goal="CONFIRM_AVAILABLE",
        )
        assert result.passed is False

    def test_acknowledge_goal_covered(self) -> None:
        draft = (
            f"Dear Alice,\n\n"
            f"{AVAIL_NOT_CHECKED} We can arrange special touches for your event.\n\n{SIGNOFF}"
        )
        result = _validate(
            draft,
            approved_blocks=[AVAIL_NOT_CHECKED, SIGNOFF],
            availability_contract="NOT_CHECKED",
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        )
        assert result.passed is False
