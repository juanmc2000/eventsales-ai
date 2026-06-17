"""Tests for CustomerTypeResolver (CUST-002)."""

import pytest

from app.modules.enquiries.customer_type_resolver import (
    ALL_RESOLVED_TYPES,
    METHOD_AGENCY_KEYWORD_DOMAIN,
    METHOD_COMMISSION_TEXT_SIGNAL,
    METHOD_CONSUMER_DOMAIN_SOCIAL,
    METHOD_CORPORATE_CONTEXT_TEXT,
    METHOD_SOCIAL_CONTEXT_TEXT,
    METHOD_EXTRACTION_CORPORATE,
    METHOD_EXTRACTION_SOCIAL,
    METHOD_KNOWN_AGENCY_DOMAIN,
    METHOD_KNOWN_CORPORATE_DOMAIN,
    METHOD_NO_SIGNAL,
    RULE_ID_1_KNOWN_AGENCY_DOMAIN,
    RULE_ID_2_COMMISSION_TEXT,
    RULE_ID_2B_CORPORATE_CONTEXT,
    RULE_ID_2C_SOCIAL_CONTEXT,
    RULE_ID_3_KNOWN_CORPORATE_DOMAIN,
    RULE_ID_4_EXTRACTION_CORPORATE,
    RULE_ID_5_CONSUMER_DOMAIN,
    RULE_ID_6_AGENCY_KEYWORD_DOMAIN,
    RULE_ID_7_EXTRACTION_SOCIAL,
    RULE_ID_8_NO_SIGNAL,
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
        # Personal dinner from gmail — no corporate or social signal keywords — still social via domain
        domain = classify("amy@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Hi, do you have availability for dinner for 8? It's a family gathering.",
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


# ── Rule 2c: Social context text signal ──────────────────────────────────────


class TestRule2cSocialContextText:
    """Personal occasion keywords classify as social regardless of sender domain."""

    def test_birthday_from_corporate_domain_resolves_social(self):
        """email_13 regression: birthday dinner from google.com must be social."""
        domain = classify("user@google.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Hi, I'm looking for dinner for a birthday for 12 people, any Friday in August.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT
        assert result.confidence >= 0.85

    def test_mums_birthday_from_corporate_domain_resolves_social(self):
        """email_24 regression: mum's birthday from amazon.com must be social."""
        domain = classify("user@amazon.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Hi, do you have lunch for 6 on 06/20? It's for my mum's birthday.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_baby_shower_from_corporate_domain_resolves_social(self):
        """email_54 regression: baby shower from deloitte.com must be social."""
        domain = classify("user@deloitte.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Hello, I'm arranging a baby shower for 15 ladies. Any weekend next month for lunch.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_birthday_lunch_from_corporate_domain_resolves_social(self):
        """email_56 regression: birthday lunch from barclays.co.uk must be social."""
        domain = classify("user@barclays.co.uk")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Hi, can you fit 13 of us on 30 June for a birthday lunch?",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_flatmate_birthday_from_corporate_domain_resolves_social(self):
        """email_58 regression: flatmate's birthday from kpmg.com must be social."""
        domain = classify("user@kpmg.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Hey, do you have a table for 10 for my flatmate's birthday? Dinner ideally.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_baby_naming_from_ambiguous_domain_resolves_social(self):
        """email_80 regression: baby naming lunch from londonbusinessgroup.com must be social."""
        domain = classify("user@londonbusinessgroup.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Hello, I'm arranging a baby naming lunch for 17 on 12/7.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_client_thank_you_from_consumer_domain_resolves_corporate(self):
        """email_52 regression: client thank-you meal from hotmail.com must be corporate."""
        domain = classify("user@hotmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Good afternoon, this is for a small client thank-you meal, 10 guests.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_client_thank_you_lunch_from_consumer_domain_resolves_corporate(self):
        """email_62 regression: client thank-you lunch from icloud.com must be corporate."""
        domain = classify("user@icloud.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Could I book lunch for 12 on 8/6? It's for a client thank-you lunch.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_corporate_context_beats_social_context(self):
        """Rule 2b fires before Rule 2c: board meeting birthday stays corporate."""
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="unknown",
            domain_classification=domain,
            enquiry_text="We're hosting a board meeting breakfast. It also happens to be the CEO's birthday.",
        )
        assert result.resolved_type == RESOLVED_CORPORATE
        assert result.resolution_method == METHOD_CORPORATE_CONTEXT_TEXT

    def test_birthday_from_consumer_domain_resolves_social_via_rule_2c(self):
        """Birthday from gmail hits Rule 2c (social text) before Rule 5 (consumer domain)."""
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="social",
            domain_classification=domain,
            enquiry_text="Dinner for 8 please — it's a birthday celebration.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_hen_do_from_corporate_domain_resolves_social(self):
        domain = classify("user@hsbc.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="I'm organising a hen do for my colleague — dinner for 12.",
        )
        assert result.resolved_type == RESOLVED_SOCIAL
        assert result.resolution_method == METHOD_SOCIAL_CONTEXT_TEXT

    def test_evidence_contains_social_signals(self):
        domain = classify("user@deloitte.com")
        result = CustomerTypeResolver.resolve(
            audience_type_from_extraction="corporate",
            domain_classification=domain,
            enquiry_text="Lunch for 15 — it's a baby shower.",
        )
        assert any("baby shower" in e for e in result.evidence)


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
        # RESP-082: structured classification metadata
        assert hasattr(result, "rule_id")
        assert hasattr(result, "reason")

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


# ── RESP-082: rule_id and reason metadata ─────────────────────────────────────


class TestRuleIdAndReasonMetadata:
    """RESP-082: Verify structured classification metadata per rule."""

    def test_rule_1_known_agency_domain(self):
        domain = classify("planner@eventconcepts.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.rule_id == RULE_ID_1_KNOWN_AGENCY_DOMAIN
        assert "agency" in result.reason.lower()
        assert result.reason != ""

    def test_rule_2_commission_text(self):
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve("unknown", domain, "my client is looking for a venue")
        assert result.rule_id == RULE_ID_2_COMMISSION_TEXT
        assert "my client" in result.reason.lower() or "commission" in result.reason.lower() or "agency" in result.reason.lower()

    def test_rule_2b_corporate_context(self):
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve("unknown", domain, "I need a room for a board meeting")
        assert result.rule_id == RULE_ID_2B_CORPORATE_CONTEXT
        assert "corporate" in result.reason.lower() or "board meeting" in result.reason.lower()

    def test_rule_2c_social_context(self):
        domain = classify("user@ibm.com")
        result = CustomerTypeResolver.resolve("corporate", domain, "planning a birthday dinner for my team")
        assert result.rule_id == RULE_ID_2C_SOCIAL_CONTEXT
        assert "social" in result.reason.lower() or "birthday" in result.reason.lower()

    def test_rule_3_known_corporate_domain(self):
        domain = classify("user@ibm.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.rule_id == RULE_ID_3_KNOWN_CORPORATE_DOMAIN
        assert "corporate" in result.reason.lower() or "domain" in result.reason.lower()

    def test_rule_4_extraction_corporate(self):
        domain = classify("user@unknownplace.io")
        result = CustomerTypeResolver.resolve("corporate", domain)
        assert result.rule_id == RULE_ID_4_EXTRACTION_CORPORATE
        assert "corporate" in result.reason.lower() or "extraction" in result.reason.lower()

    def test_rule_5_consumer_domain(self):
        domain = classify("user@gmail.com")
        result = CustomerTypeResolver.resolve("unknown", domain)
        assert result.rule_id == RULE_ID_5_CONSUMER_DOMAIN
        assert "consumer" in result.reason.lower() or "social" in result.reason.lower()

    def test_rule_6_agency_keyword_domain(self):
        # Use a domain with agency keyword but not an exact known agency domain
        domain = classify("user@mycorporateevents.com")
        result = CustomerTypeResolver.resolve("social", domain)
        assert result.rule_id == RULE_ID_6_AGENCY_KEYWORD_DOMAIN
        assert "agency" in result.reason.lower() or "keyword" in result.reason.lower()

    def test_rule_7_extraction_social(self):
        domain = classify("user@unknownplace.io")
        result = CustomerTypeResolver.resolve("social", domain)
        assert result.rule_id == RULE_ID_7_EXTRACTION_SOCIAL
        assert "social" in result.reason.lower() or "extraction" in result.reason.lower()

    def test_rule_8_no_signal_unknown(self):
        result = CustomerTypeResolver.resolve("unknown", None)
        assert result.rule_id == RULE_ID_8_NO_SIGNAL
        assert result.reason != ""

    def test_reason_is_string(self):
        cases = [
            ("unknown", None, None),
            ("corporate", classify("user@gmail.com"), None),
            ("unknown", classify("user@gmail.com"), "birthday dinner"),
            ("social", classify("user@ibm.com"), "birthday dinner"),
            ("unknown", classify("user@ibm.com"), "board meeting"),
        ]
        for extraction, domain, text in cases:
            result = CustomerTypeResolver.resolve(extraction, domain, text)
            assert isinstance(result.rule_id, str)
            assert isinstance(result.reason, str)
            assert len(result.rule_id) > 0
            assert len(result.reason) > 0

    def test_rule_id_starts_with_rule_prefix(self):
        cases = [
            ("unknown", None, None),
            ("corporate", classify("user@gmail.com"), "client dinner"),
            ("unknown", classify("user@gmail.com"), "birthday"),
            ("unknown", classify("user@ibm.com"), None),
            ("unknown", classify("planner@eventconcepts.com"), None),
        ]
        for extraction, domain, text in cases:
            result = CustomerTypeResolver.resolve(extraction, domain, text)
            assert result.rule_id.startswith("rule_"), f"Expected rule_ prefix, got: {result.rule_id}"

    def test_luxury_not_classified(self):
        """Luxury classification is out of scope for resolver; no luxury rule_id expected."""
        result = CustomerTypeResolver.resolve("unknown", None)
        assert "luxury" not in result.rule_id


# ── TEST-031: Audience boundary fixture cases ──────────────────────────────────


import json
import pathlib

_BOUNDARY_FIXTURE = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
    / "tests" / "data" / "audience_classification_boundary_cases.json"
)


def _load_boundary_cases() -> list[dict]:
    if not _BOUNDARY_FIXTURE.exists():
        return []
    with open(_BOUNDARY_FIXTURE) as f:
        return json.load(f)["records"]


class TestAudienceBoundaryCases:
    """TEST-031: 40-record audience-boundary fixture regression suite.

    Covers corporate-from-personal-domain, social-from-corporate-domain,
    agency+social, luxury-social, private/family-office, PA/EA bookings,
    client thank-you edge cases, event-manager wording, and helping-a-friend.
    """

    def test_fixture_loads_and_has_40_records(self):
        cases = _load_boundary_cases()
        assert len(cases) == 40, f"Expected 40 boundary cases, got {len(cases)}"

    def test_all_cases_pass(self):
        cases = _load_boundary_cases()
        if not cases:
            pytest.skip("Boundary fixture not found — skipping")
        failures: list[str] = []
        for rec in cases:
            domain = SenderDomainClassificationService.classify(rec["sender_email"])
            result = CustomerTypeResolver.resolve(
                rec.get("extraction_audience_type", "unknown"),
                domain,
                rec.get("enquiry_text", ""),
            )
            if result.resolved_type != rec["expected_audience_type"]:
                failures.append(
                    f"{rec['case_id']}: expected={rec['expected_audience_type']} "
                    f"actual={result.resolved_type} | {rec['description']}"
                )
        assert not failures, "Boundary case failures:\n" + "\n".join(failures)

    def test_corporate_from_personal_domain_cases(self):
        cases = [c for c in _load_boundary_cases() if c["category"] == "corporate_from_personal_domain"]
        assert len(cases) == 5
        for rec in cases:
            domain = SenderDomainClassificationService.classify(rec["sender_email"])
            result = CustomerTypeResolver.resolve(
                rec.get("extraction_audience_type", "unknown"), domain, rec["enquiry_text"]
            )
            assert result.resolved_type == "corporate", (
                f"{rec['case_id']}: corporate context from personal domain should resolve to corporate"
            )

    def test_social_from_corporate_domain_cases(self):
        cases = [c for c in _load_boundary_cases() if c["category"] == "social_from_corporate_domain"]
        assert len(cases) == 5
        for rec in cases:
            domain = SenderDomainClassificationService.classify(rec["sender_email"])
            result = CustomerTypeResolver.resolve(
                rec.get("extraction_audience_type", "unknown"), domain, rec["enquiry_text"]
            )
            assert result.resolved_type == "social", (
                f"{rec['case_id']}: social occasion from corporate domain should resolve to social"
            )

    def test_agency_plus_social_cases(self):
        cases = [c for c in _load_boundary_cases() if c["category"] == "agency_plus_social"]
        assert len(cases) == 5
        for rec in cases:
            domain = SenderDomainClassificationService.classify(rec["sender_email"])
            result = CustomerTypeResolver.resolve(
                rec.get("extraction_audience_type", "unknown"), domain, rec["enquiry_text"]
            )
            assert result.resolved_type == "agency", (
                f"{rec['case_id']}: agency signal should override social signal"
            )

    def test_client_thank_you_before_birthday(self):
        cases = [c for c in _load_boundary_cases() if c["case_id"] == "boundary_31"]
        assert len(cases) == 1
        rec = cases[0]
        domain = SenderDomainClassificationService.classify(rec["sender_email"])
        result = CustomerTypeResolver.resolve(
            rec.get("extraction_audience_type", "unknown"), domain, rec["enquiry_text"]
        )
        assert result.resolved_type == "corporate", (
            "client thank-you should take precedence over birthday (Rule 2b before Rule 2c)"
        )

    def test_no_signal_resolves_to_unknown(self):
        cases = [c for c in _load_boundary_cases() if c["category"] == "no_signal_unknown"]
        assert len(cases) == 1
        rec = cases[0]
        domain = SenderDomainClassificationService.classify(rec["sender_email"])
        result = CustomerTypeResolver.resolve(
            rec.get("extraction_audience_type", "unknown"), domain, rec["enquiry_text"]
        )
        assert result.resolved_type == "unknown"

    def test_all_audience_types_represented(self):
        cases = _load_boundary_cases()
        types_found = {c["expected_audience_type"] for c in cases}
        assert "social" in types_found
        assert "corporate" in types_found
        assert "agency" in types_found
        assert "unknown" in types_found
