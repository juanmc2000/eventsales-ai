"""Tests for SenderDomainClassificationService (CUST-001)."""

import pytest

from app.modules.enquiries.sender_domain_classification_service import (
    AUDIENCE_AGENCY,
    AUDIENCE_CONSUMER,
    AUDIENCE_CORPORATE,
    AUDIENCE_UNKNOWN,
    ALL_AUDIENCE_TYPES,
    REASON_AGENCY_KEYWORD,
    REASON_KNOWN_AGENCY_DOMAIN,
    REASON_KNOWN_CONSUMER_DOMAIN,
    REASON_KNOWN_CORPORATE_DOMAIN,
    REASON_NO_MATCH,
    DomainClassificationResult,
    SenderDomainClassificationService,
)


# ── Constants ──────────────────────────────────────────────────────────────────


class TestConstants:
    def test_all_audience_types_are_defined(self):
        assert ALL_AUDIENCE_TYPES == {"agency", "corporate", "consumer", "unknown"}

    def test_audience_constants_match_set(self):
        assert AUDIENCE_AGENCY in ALL_AUDIENCE_TYPES
        assert AUDIENCE_CORPORATE in ALL_AUDIENCE_TYPES
        assert AUDIENCE_CONSUMER in ALL_AUDIENCE_TYPES
        assert AUDIENCE_UNKNOWN in ALL_AUDIENCE_TYPES


# ── Consumer domains ──────────────────────────────────────────────────────────


class TestConsumerDomains:
    @pytest.mark.parametrize("email,expected_domain", [
        ("alice@gmail.com", "gmail.com"),
        ("bob@hotmail.com", "hotmail.com"),
        ("carol@yahoo.com", "yahoo.com"),
        ("dave@outlook.com", "outlook.com"),
        ("eve@icloud.com", "icloud.com"),
        ("frank@live.co.uk", "live.co.uk"),
        ("grace@hotmail.co.uk", "hotmail.co.uk"),
        ("henry@yahoo.co.uk", "yahoo.co.uk"),
        ("iris@protonmail.com", "protonmail.com"),
        ("jack@msn.com", "msn.com"),
    ])
    def test_known_consumer_domains(self, email, expected_domain):
        result = SenderDomainClassificationService.classify(email)
        assert result.audience_type == AUDIENCE_CONSUMER
        assert result.confidence >= 0.9
        assert result.match_reason == REASON_KNOWN_CONSUMER_DOMAIN
        assert result.domain == expected_domain

    def test_consumer_email_uppercase_normalised(self):
        result = SenderDomainClassificationService.classify("USER@GMAIL.COM")
        assert result.audience_type == AUDIENCE_CONSUMER
        assert result.domain == "gmail.com"


# ── Corporate domains ─────────────────────────────────────────────────────────


class TestCorporateDomains:
    @pytest.mark.parametrize("email,expected_domain", [
        ("alice@microsoft.com", "microsoft.com"),
        ("bob@google.com", "google.com"),
        ("carol@ibm.com", "ibm.com"),
        ("dave@amazon.com", "amazon.com"),
        ("eve@deloitte.com", "deloitte.com"),
        ("frank@barclays.com", "barclays.com"),
        ("grace@pwc.com", "pwc.com"),
        ("henry@nhs.net", "nhs.net"),
        ("iris@bbc.co.uk", "bbc.co.uk"),
        ("jack@gov.uk", "gov.uk"),
    ])
    def test_known_corporate_domains(self, email, expected_domain):
        result = SenderDomainClassificationService.classify(email)
        assert result.audience_type == AUDIENCE_CORPORATE
        assert result.confidence >= 0.85
        assert result.match_reason == REASON_KNOWN_CORPORATE_DOMAIN
        assert result.domain == expected_domain

    def test_corporate_email_uppercase_normalised(self):
        result = SenderDomainClassificationService.classify("CEO@MICROSOFT.COM")
        assert result.audience_type == AUDIENCE_CORPORATE
        assert result.domain == "microsoft.com"


# ── Agency domains ────────────────────────────────────────────────────────────


class TestAgencyDomains:
    @pytest.mark.parametrize("email,expected_reason", [
        ("alice@ashfield.co.uk", REASON_KNOWN_AGENCY_DOMAIN),
        ("bob@eventconcepts.com", REASON_KNOWN_AGENCY_DOMAIN),
        ("carol@bcd-meetings.com", REASON_KNOWN_AGENCY_DOMAIN),
        ("dave@cvent.com", REASON_KNOWN_AGENCY_DOMAIN),
    ])
    def test_known_agency_domains(self, email, expected_reason):
        result = SenderDomainClassificationService.classify(email)
        assert result.audience_type == AUDIENCE_AGENCY
        assert result.confidence >= 0.9
        assert result.match_reason == expected_reason

    @pytest.mark.parametrize("email", [
        "alice@premierevents.co.uk",
        "bob@londonevents.com",
        "carol@venuehire.co.uk",
        "dave@conferenceplanning.com",
        "eve@hospitalitysolutions.co.uk",
    ])
    def test_agency_keyword_in_domain(self, email):
        result = SenderDomainClassificationService.classify(email)
        assert result.audience_type == AUDIENCE_AGENCY
        assert result.confidence >= 0.7
        assert result.match_reason == REASON_AGENCY_KEYWORD

    def test_agency_takes_precedence_over_corporate_keyword(self):
        # eventconcepts.com is in known agency list — must resolve to agency
        result = SenderDomainClassificationService.classify("planner@eventconcepts.com")
        assert result.audience_type == AUDIENCE_AGENCY
        assert result.match_reason == REASON_KNOWN_AGENCY_DOMAIN


# ── Unknown domains ───────────────────────────────────────────────────────────


class TestUnknownDomains:
    @pytest.mark.parametrize("email", [
        "alice@boutiquebakery.co.uk",
        "bob@localplumber.net",
        "carol@randomcompany.io",
        "dave@unknowndomain.xyz",
    ])
    def test_unknown_domains(self, email):
        result = SenderDomainClassificationService.classify(email)
        assert result.audience_type == AUDIENCE_UNKNOWN
        assert result.confidence == 0.0
        assert result.match_reason == REASON_NO_MATCH

    def test_none_email_returns_unknown(self):
        result = SenderDomainClassificationService.classify(None)
        assert result.audience_type == AUDIENCE_UNKNOWN
        assert result.confidence == 0.0
        assert result.domain == ""

    def test_empty_string_returns_unknown(self):
        result = SenderDomainClassificationService.classify("")
        assert result.audience_type == AUDIENCE_UNKNOWN

    def test_no_at_sign_returns_unknown(self):
        result = SenderDomainClassificationService.classify("notanemail")
        assert result.audience_type == AUDIENCE_UNKNOWN

    def test_whitespace_only_returns_unknown(self):
        result = SenderDomainClassificationService.classify("   ")
        assert result.audience_type == AUDIENCE_UNKNOWN


# ── Domain extraction ─────────────────────────────────────────────────────────


class TestDomainExtraction:
    def test_extracts_domain_from_standard_email(self):
        domain = SenderDomainClassificationService._extract_domain("user@example.com")
        assert domain == "example.com"

    def test_extracts_domain_lowercased(self):
        domain = SenderDomainClassificationService._extract_domain("User@EXAMPLE.COM")
        assert domain == "example.com"

    def test_handles_plus_addressing(self):
        domain = SenderDomainClassificationService._extract_domain("user+filter@gmail.com")
        assert domain == "gmail.com"

    def test_handles_subdomain_emails(self):
        domain = SenderDomainClassificationService._extract_domain("user@mail.company.co.uk")
        assert domain == "mail.company.co.uk"

    def test_none_returns_none(self):
        assert SenderDomainClassificationService._extract_domain(None) is None

    def test_empty_returns_none(self):
        assert SenderDomainClassificationService._extract_domain("") is None

    def test_no_at_returns_none(self):
        assert SenderDomainClassificationService._extract_domain("nodomain") is None


# ── Result shape ──────────────────────────────────────────────────────────────


class TestResultShape:
    def test_result_has_all_fields(self):
        result = SenderDomainClassificationService.classify("user@gmail.com")
        assert isinstance(result, DomainClassificationResult)
        assert hasattr(result, "audience_type")
        assert hasattr(result, "confidence")
        assert hasattr(result, "match_reason")
        assert hasattr(result, "domain")

    def test_confidence_is_float(self):
        result = SenderDomainClassificationService.classify("user@gmail.com")
        assert isinstance(result.confidence, float)

    def test_audience_type_always_in_known_set(self):
        emails = [
            "user@gmail.com",
            "user@microsoft.com",
            "user@eventconcepts.com",
            "user@unknownplace.io",
            None,
            "",
        ]
        for email in emails:
            result = SenderDomainClassificationService.classify(email)
            assert result.audience_type in ALL_AUDIENCE_TYPES

    def test_no_llm_calls_made(self):
        # Verifies the service is purely deterministic by checking it does not
        # import or invoke any AI gateway module.
        import app.modules.enquiries.sender_domain_classification_service as svc_module
        source = open(svc_module.__file__).read()
        assert "AIGateway" not in source
        assert "anthropic" not in source
