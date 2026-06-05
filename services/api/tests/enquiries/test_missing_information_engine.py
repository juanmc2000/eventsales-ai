"""Tests for MissingInformationDecisionEngine (ORCH-003)."""

from __future__ import annotations

import pytest

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
)
from app.modules.enquiries.missing_information_engine import (
    WEBFORM_THRESHOLD,
    MissingInformationDecisionEngine,
    MissingInformationResult,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _decide(**kwargs) -> MissingInformationResult:
    defaults = {
        "date_status": STATUS_RESOLVED,
        "date_clarification_question": None,
        "guest_count_present": True,
        "occasion_understood": True,
        "meal_period_present": True,
        "contact_details_required": False,
        "contact_details_present": True,
    }
    defaults.update(kwargs)
    return MissingInformationDecisionEngine.decide(**defaults)


# ── MissingInformationResult ──────────────────────────────────────────────────


def test_to_dict_has_all_keys():
    r = MissingInformationResult()
    d = r.to_dict()
    assert set(d.keys()) == {
        "missing_fields",
        "critical_missing_fields",
        "clarification_questions",
        "can_ask_by_email",
        "should_send_webform",
        "missing_info_reason",
    }


def test_requires_action_false_when_nothing_missing():
    r = MissingInformationResult()
    assert r.requires_action is False


def test_requires_action_true_when_missing_fields():
    r = MissingInformationResult(missing_fields=["guest_count"])
    assert r.requires_action is True


# ── Complete enquiry ──────────────────────────────────────────────────────────


def test_complete_enquiry_produces_no_action():
    r = _decide()
    assert r.missing_fields == []
    assert r.critical_missing_fields == []
    assert r.clarification_questions == []
    assert r.can_ask_by_email is False
    assert r.should_send_webform is False


# ── Date: ambiguous ───────────────────────────────────────────────────────────


def test_ambiguous_date_produces_date_confirmation_question():
    r = _decide(
        date_status=STATUS_AMBIGUOUS,
        date_clarification_question="Did you mean 7 June or 6 July?",
    )
    assert "date_confirmation" in r.critical_missing_fields
    assert "date_confirmation" in r.missing_fields
    assert any("June" in q or "July" in q for q in r.clarification_questions)
    assert r.can_ask_by_email is True
    assert r.should_send_webform is False


def test_ambiguous_date_without_custom_question_uses_generic():
    r = _decide(date_status=STATUS_AMBIGUOUS)
    assert r.critical_missing_fields == ["date_confirmation"]
    assert len(r.clarification_questions) == 1
    assert "clarify" in r.clarification_questions[0].lower()


# ── Date: resolved with confirmation ─────────────────────────────────────────


def test_resolved_with_confirmation_date():
    r = _decide(
        date_status=STATUS_RESOLVED_WITH_CONFIRMATION,
        date_clarification_question="Can you confirm you meant 14 June?",
    )
    assert "date_confirmation" in r.critical_missing_fields
    assert r.can_ask_by_email is True


# ── Date: unknown / missing ───────────────────────────────────────────────────


def test_unknown_date_asks_for_date():
    r = _decide(date_status=STATUS_UNKNOWN)
    assert "event_date" in r.critical_missing_fields
    assert any("book" in q.lower() or "date" in q.lower() for q in r.clarification_questions)
    assert r.can_ask_by_email is True


def test_none_date_status_treated_as_unknown():
    r = _decide(date_status=None)
    assert "event_date" in r.critical_missing_fields


# ── Guest count ───────────────────────────────────────────────────────────────


def test_missing_guest_count_produces_question():
    r = _decide(guest_count_present=False)
    assert "guest_count" in r.critical_missing_fields
    assert any("guest" in q.lower() for q in r.clarification_questions)
    assert r.can_ask_by_email is True
    assert r.should_send_webform is False


# ── Non-critical fields ───────────────────────────────────────────────────────


def test_missing_occasion_goes_to_missing_fields_only():
    r = _decide(occasion_understood=False)
    assert "occasion" in r.missing_fields
    assert "occasion" not in r.critical_missing_fields
    assert r.critical_missing_fields == []


def test_missing_meal_period_goes_to_missing_fields_only():
    r = _decide(meal_period_present=False)
    assert "meal_period" in r.missing_fields
    assert "meal_period" not in r.critical_missing_fields
    assert r.critical_missing_fields == []


# ── Webform threshold ─────────────────────────────────────────────────────────


def test_webform_threshold_constant_is_three():
    assert WEBFORM_THRESHOLD == 3


def test_three_critical_fields_recommend_webform():
    r = _decide(
        date_status=STATUS_UNKNOWN,      # critical: event_date
        guest_count_present=False,        # critical: guest_count
        contact_details_required=True,
        contact_details_present=False,    # critical: contact_details
    )
    assert r.should_send_webform is True
    assert r.can_ask_by_email is False
    assert len(r.critical_missing_fields) >= 3


def test_two_critical_fields_prefer_email():
    r = _decide(
        date_status=STATUS_UNKNOWN,   # critical: event_date
        guest_count_present=False,     # critical: guest_count
    )
    assert r.should_send_webform is False
    assert r.can_ask_by_email is True
    assert len(r.critical_missing_fields) == 2


def test_one_critical_field_prefers_email():
    r = _decide(guest_count_present=False)
    assert r.can_ask_by_email is True
    assert r.should_send_webform is False


# ── Contact details ───────────────────────────────────────────────────────────


def test_contact_details_not_required_when_flag_false():
    r = _decide(contact_details_required=False, contact_details_present=False)
    assert "contact_details" not in r.critical_missing_fields


def test_contact_details_required_and_missing():
    r = _decide(contact_details_required=True, contact_details_present=False)
    assert "contact_details" in r.critical_missing_fields
    assert any("contact" in q.lower() for q in r.clarification_questions)


# ── Reason string ─────────────────────────────────────────────────────────────


def test_reason_mentions_critical_fields():
    r = _decide(guest_count_present=False)
    assert "guest_count" in r.missing_info_reason


def test_reason_mentions_webform_when_threshold_reached():
    r = _decide(
        date_status=STATUS_UNKNOWN,
        guest_count_present=False,
        contact_details_required=True,
        contact_details_present=False,
    )
    assert "webform" in r.missing_info_reason.lower()
