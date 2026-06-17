"""Tests for CustomerTypeResolver (CUST-002)."""

import pytest

from app.modules.enquiries.customer_type_resolver import (
    ALL_RESOLVED_TYPES,
    METHOD_AGENCY_KEYWORD_DOMAIN,
    METHOD_COMMISSION_TEXT_SIGNAL,
    METHOD_CONSUMER_DOMAIN_SOCIAL,
    METHOD_CORPORATE_CONTEXT_TEXT,
    METHOD_EXTRACTION_CORPORATE,
    METHOD_EXTRACTION_SOCIAL,
    METHOD_KNOWN_AGENCY_DOMAIN,
    METHOD_KNOWN_CORPORATE_DOMAIN,
    METHOD_NO_SIGNAL,
    RESOLVED_AGENCY,
    RESOLVED_CORPORATE,
    RESOLVED_SOCIAL,
    RESOLVED_UNKNOWN,
    CustomerTypeResolution,
    CustomerTypeResolver,
)
from app.modules.enquiries.sender_domain_classification_service import (
    SenderDomainClassificationService,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def classify(email: str):
    return SenderDomainClassificationService.classify(email)


# ── Constants ──────────────────────────────────────────────────────────────────


class TestConstants:
    def test_all_resolved_types(self):
        assert ALL_RESOLVED_TYPES == {"agency", "corporate", "social", "unknown"}


# ── Rule 1: Known agency domain ────────────────────────────────────────────────


class TestRule1KnownAgencyDomain:
    def test_known_agency_domain_resolves_to_agency(self):
        domain = classify("planner@eventconcepts.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_KNOWN_AGENCY_DOMAIN
        assert result.confidence >= 0.9

    def test_known_agency_domain_overrides_extraction(self):
        # Even if extraction says social, domain wins (Rule 1)
        domain = classify("alice@ashfield.co.uk")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_KNOWN_AGENCY_DOMAIN

    def test_known_agency_domain_includes_evidence(self):
        domain = classify("alice@ashfield.co.uk")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert len(result.evidence) > 0
        assert any("agency" in e for e in result.evidence)


# ── Rule 2: Commission text signal ───────────────────────────────────────────


class TestRule2CommissionTextSignal:
    def test_commission_keyword_resolves_to_agency(self):
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=domain,
            enquiry_text="We are enquiring on behalf of our client for a team dinner.",
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_COMMISSION_TEXT_SIGNAL

    def test_venue_find_keyword_resolves_to_agency(self):
        domain = classify("alice@boutiquebakery.co.uk")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=domain,
            enquiry_text="We are doing a venue find for a corporate dinner next March.",
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_COMMISSION_TEXT_SIGNAL

    def test_commission_word_triggers_agency(self):
        domain = classify("planner@someeventco.co.uk")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Please note that we charge a commission of 10% on all bookings.",
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_COMMISSION_TEXT_SIGNAL

    def test_rfp_keyword_triggers_agency(self):
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=None,
            enquiry_text="This is an RFP for a conference dinner for 80 delegates.",
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_COMMISSION_TEXT_SIGNAL

    def test_no_commission_keyword_does_not_trigger(self):
        domain = classify("alice@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="I am planning a birthday dinner for 20 friends.",
        )
        # Consumer domain → social (Rule 5), not commission
        assert result.resolution_method != METHOD_COMMISSION_TEXT_SIGNAL

    def test_evidence_lists_triggered_signals(self):
        domain = classify("alice@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=domain,
            enquiry_text="We are organising a venue find for our clients.",
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert any("venue find" in e for e in result.evidence)


# ── Rule 2b: Corporate context text signal (RESP-080) ────────────────────────


class TestRule2bCorporateContextText:
    """Board/client/work-meeting keywords classify as corporate regardless of domain."""

    def test_board_meeting_gmail_resolves_corporate(self):
        # email_57 / email_72 scenario: board meeting from gmail/protonmail
        domain = classify("elaine@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Good morning, I need to book breakfast for 7. It's a board meeting.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT
        assert result.confidence >= 0.85

    def test_board_meeting_protonmail_resolves_corporate(self):
        domain = classify("sophie.turner@proton.me")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="It's a board meeting. Morning, maybe 8am.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_client_dinner_personal_domain_resolves_corporate(self):
        domain = classify("user@hotmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="I need dinner for 10 on Friday. This is a client dinner.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_client_meeting_resolves_corporate(self):
        domain = classify("user@icloud.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=domain,
            enquiry_text="Booking for a client meeting, 6 guests, Wednesday lunch.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_work_team_meal_resolves_corporate(self):
        domain = classify("sarah.green@aol.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Hi, can I book for a work team meal next Weds for 11 people?",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_business_breakfast_resolves_corporate(self):
        domain = classify("user@yahoo.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Looking to arrange a business breakfast for 8 next Tuesday.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_team_meeting_resolves_corporate(self):
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Lunch for 12 — team meeting offsite.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_agency_commission_text_still_beats_corporate_context(self):
        # If both corporate context AND agency commission text are present,
        # agency (Rule 2) takes precedence over corporate context (Rule 2b).
        domain = classify("planner@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="I am working on behalf of my client for a client dinner, 15 guests.",
        )
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_COMMISSION_TEXT_SIGNAL

    def test_social_occasion_no_corporate_keywords_stays_social(self):
        # Birthday dinner from gmail — no corporate keywords — still social
        domain = classify("amy@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Hi, do you have availability for dinner for 8? It's my sister's birthday.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_CONSUMER_DOMAIN_SOCIAL

    def test_evidence_contains_triggered_signals(self):
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="This is for a board meeting breakfast, 7 guests.",
        )
        assert any("board meeting" in e for e in result.evidence)

    def test_email_57_scenario(self):
        """Regression: email_57 — board meeting from proton.me must be corporate."""
        domain = classify("sophie.turner@proton.me")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text=(
                "Good morning, I need to book a breakfast meeting for 7 on the 24th of this month. "
                "Morning, maybe 8am or 8.30. It's a board meeting. Regards, Elaine"
            ),
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_email_72_scenario(self):
        """Regression: email_72 — board meeting from gmail must be corporate."""
        domain = classify("megan.clark@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text=(
                "Good morning, could we book breakfast for 7 on 6/9? It's a board meeting. "
                "Date format might be ambiguous, so please confirm. Around 8.30. Regards, Eva"
            ),
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT


# ── Rule 3: Known corporate domain ───────────────────────────────────────────


class TestRule3KnownCorporateDomain:
    def test_corporate_domain_resolves_to_corporate(self):
        domain = classify("alice@microsoft.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=domain,
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_KNOWN_CORPORATE_DOMAIN
        assert result.confidence >= 0.85

    def test_corporate_domain_overrides_social_extraction(self):
        domain = classify("bob@google.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_KNOWN_CORPORATE_DOMAIN

    def test_corporate_domain_checked_after_commission_text(self):
        # Commission text (Rule 2) wins over corporate domain (Rule 3)
        domain = classify("planner@ibm.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="We are doing a venue find for a client.",
        )
        # Commission text triggers Rule 2 before Rule 3
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_COMMISSION_TEXT_SIGNAL


# ── Rule 4: Extraction says corporate ────────────────────────────────────────


class TestRule4ExtractionCorporate:
    def test_extraction_corporate_with_no_domain(self):
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=None,
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_EXTRACTION_CORPORATE
        assert result.confidence == 0.75

    def test_extraction_corporate_with_unknown_domain(self):
        domain = classify("alice@somebusiness.io")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_EXTRACTION_CORPORATE

    def test_extraction_corporate_overridden_by_consumer_domain(self):
        # Consumer domain (Rule 5 check) — BUT Rule 4 runs first.
        # Rule 4 excludes consumer domain (domain_type not in (AUDIENCE_CONSUMER,)).
        domain = classify("alice@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
        )
        # Rule 4 skips when domain is consumer; falls through to Rule 5
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_CONSUMER_DOMAIN_SOCIAL


# ── Rule 5: Consumer domain → social ─────────────────────────────────────────


class TestRule5ConsumerDomain:
    def test_gmail_resolves_to_social(self):
        domain = classify("alice@gmail.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_CONSUMER_DOMAIN_SOCIAL
        assert result.confidence >= 0.75

    def test_hotmail_resolves_to_social(self):
        domain = classify("bob@hotmail.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_CONSUMER_DOMAIN_SOCIAL

    def test_yahoo_resolves_to_social(self):
        domain = classify("carol@yahoo.co.uk")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.resolved_type == RESOLVED_SOCIAL

    def test_icloud_resolves_to_social(self):
        domain = classify("dave@icloud.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.resolved_type == RESOLVED_SOCIAL


# ── Rule 6: Extraction says social ───────────────────────────────────────────


class TestRule6ExtractionSocial:
    def test_extraction_social_with_unknown_domain(self):
        domain = classify("alice@unknowndomain.xyz")
        result = CustomerTypeResolver.resolve("social", domain)
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_EXTRACTION_SOCIAL
        assert result.confidence == 0.65

    def test_extraction_social_with_no_domain(self):
        result = CustomerTypeResolver.resolve("social", None)
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_EXTRACTION_SOCIAL


# ── Rule 7: Agency keyword domain ────────────────────────────────────────────


class TestRule7AgencyKeywordDomain:
    def test_agency_keyword_domain_resolves_to_agency(self):
        domain = classify("alice@londonevents.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.resolution_method == METHOD_AGENCY_KEYWORD_DOMAIN
        assert result.confidence == 0.70

    def test_agency_keyword_domain_lower_confidence_than_exact_match(self):
        exact = classify("alice@ashfield.co.uk")
        keyword = classify("alice@londonevents.com")
        r_exact = CustomerTypeResolver.resolve("unknown", exact)
        r_keyword = CustomerTypeResolver.resolve("unknown", keyword)
        assert r_exact.confidence > r_keyword.confidence


# ── Rule 8: No signal / fallback ─────────────────────────────────────────────


class TestRule8NoSignal:
    def test_no_signal_returns_unknown(self):
        domain = classify("alice@boutiquebakery.co.uk")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.resolved_type == RESOLVED_UNKNOWN
        assert result.confidence == 0.0
        assert result.resolution_method == METHOD_NO_SIGNAL

    def test_none_extraction_and_no_domain_returns_unknown(self):
        result = CustomerTypeResolver.resolve(None, None)
        assert result.resolved_type == RESOLVED_UNKNOWN

    def test_extraction_agency_without_corroboration_returns_agency_low_confidence(self):
        domain = classify("alice@unknowndomain.xyz")
        result = CustomerTypeResolver.resolve("agency", domain)
        assert result.resolved_type == RESOLVED_AGENCY
        assert result.confidence == 0.50  # Low confidence — no corroboration
        assert result.resolution_method == METHOD_NO_SIGNAL


# ── Result shape ──────────────────────────────────────────────────────────────


class TestResultShape:
    def test_result_has_required_fields(self):
        result = CustomerTypeResolver.resolve("unknown", None)
        assert isinstance(result, CustomerTypeResolution)
        assert hasattr(result, "resolved_type")
        assert hasattr(result, "confidence")
        assert hasattr(result, "resolution_method")
        assert hasattr(result, "evidence")

    def test_resolved_type_always_in_known_set(self):
        cases = [
            ("unknown", classify("user@gmail.com"), "birthday dinner"),
            ("corporate", classify("user@microsoft.com"), None),
            ("agency", classify("user@eventconcepts.com"), None),
            ("social", classify("user@unknownplace.io"), None),
            (None, None, None),
        ]
        for extraction, domain, text in cases:
            result = CustomerTypeResolver.resolve(extraction, domain, text)
            assert result.resolved_type in ALL_RESOLVED_TYPES

    def test_confidence_is_float_between_0_and_1(self):
        cases = [
            ("unknown", classify("user@gmail.com"), None),
            ("corporate", classify("user@ibm.com"), None),
            ("unknown", classify("user@ashfield.co.uk"), None),
        ]
        for extraction, domain, text in cases:
            result = CustomerTypeResolver.resolve(extraction, domain, text)
            assert 0.0 <= result.confidence <= 1.0

    def test_evidence_is_list(self):
        result = CustomerTypeResolver.resolve("unknown", None)
        assert isinstance(result.evidence, list)

    def test_no_llm_calls_made(self):
        import app.modules.enquiries.customer_type_resolver as mod
        source = open(mod.__file__).read()
        assert "AIGateway" not in source
        assert "anthropic" not in source
