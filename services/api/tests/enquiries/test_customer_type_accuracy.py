"""Customer Type Accuracy Test Suite (CUST-004).

Measures audience classification accuracy of the CustomerTypeResolver
across a deterministic dataset covering social, corporate, and agency enquiries.

Metrics reported:
  - Overall classification accuracy (%)
  - False agency rate: non-agency cases classified as agency (%)
  - False corporate rate: non-corporate cases classified as corporate (%)

All tests are deterministic — no LLM calls.

Dataset design:
  - Social enquiries: gmail/hotmail/yahoo/icloud/outlook domains
  - Corporate enquiries: known corporate domains + corporate extraction signal
  - Agency enquiries: known agency domains + commission/agency text signals
"""

import pytest

from app.modules.enquiries.customer_type_resolver import (
    RESOLVED_AGENCY,
    RESOLVED_CORPORATE,
    RESOLVED_SOCIAL,
    RESOLVED_UNKNOWN,
    CustomerTypeResolver,
)
from app.modules.enquiries.sender_domain_classification_service import (
    SenderDomainClassificationService,
)


# ── Test dataset ──────────────────────────────────────────────────────────────
# Each entry: (description, sender_email, audience_type_from_extraction, enquiry_text, expected_type)

SOCIAL_CASES = [
    (
        "birthday dinner via gmail",
        "sarah@gmail.com",
        "social",
        "Hi, I'd like to book a private room for my 30th birthday dinner for 20 friends on Saturday 15th August.",
        RESOLVED_SOCIAL,
    ),
    (
        "anniversary dinner via hotmail",
        "james@hotmail.com",
        "social",
        "We're celebrating our 10th wedding anniversary and would love a private dining experience.",
        RESOLVED_SOCIAL,
    ),
    (
        "hen party via yahoo",
        "jessica@yahoo.co.uk",
        "social",
        "I'm organising a hen do for my best friend. Looking for a private room for about 12 ladies.",
        RESOLVED_SOCIAL,
    ),
    (
        "graduation dinner via icloud",
        "tom@icloud.com",
        "social",
        "My daughter is graduating next month and we'd love to celebrate with a family dinner for 15 people.",
        RESOLVED_SOCIAL,
    ),
    (
        "baby shower via outlook",
        "emma@outlook.com",
        "social",
        "I'm planning a baby shower lunch for about 25 guests. Can you accommodate dietary requirements?",
        RESOLVED_SOCIAL,
    ),
    (
        "birthday via hotmail co.uk",
        "mike@hotmail.co.uk",
        "social",
        "Booking a surprise birthday dinner for my wife. 8 people, Saturday evening.",
        RESOLVED_SOCIAL,
    ),
    (
        "engagement celebration via yahoo uk",
        "anna@yahoo.co.uk",
        "social",
        "My partner and I just got engaged! We'd love to celebrate with a dinner for our closest friends.",
        RESOLVED_SOCIAL,
    ),
    (
        "christmas party unknown type via gmail",
        "lucy@gmail.com",
        "unknown",
        "Looking to book our family Christmas dinner for about 18 people on 24th December.",
        RESOLVED_SOCIAL,
    ),
    (
        "retirement party via protonmail",
        "david@protonmail.com",
        "social",
        "Dad is retiring after 40 years and we'd like to organise a lovely dinner for 30 family and friends.",
        RESOLVED_SOCIAL,
    ),
    (
        "stag night via msn",
        "chris@msn.com",
        "social",
        "Planning a stag do for my mate. Need a private room for 15 lads on a Friday night.",
        RESOLVED_SOCIAL,
    ),
]

CORPORATE_CASES = [
    (
        "team dinner via microsoft",
        "alice@microsoft.com",
        "corporate",
        "Our team of 12 would like to book a private room for a team dinner to celebrate Q3 results.",
        RESOLVED_CORPORATE,
    ),
    (
        "client dinner via google",
        "bob@google.com",
        "corporate",
        "We're entertaining a key client next Thursday. A private dining room for 8 would be ideal.",
        RESOLVED_CORPORATE,
    ),
    (
        "board dinner via ibm",
        "carol@ibm.com",
        "corporate",
        "Our board of directors is meeting in London next month and we'd like to arrange a dinner for 10.",
        RESOLVED_CORPORATE,
    ),
    (
        "office party via deloitte",
        "dave@deloitte.com",
        "corporate",
        "Looking to book our department Christmas party for 50 people. Budget is flexible.",
        RESOLVED_CORPORATE,
    ),
    (
        "investor dinner via barclays",
        "eve@barclays.com",
        "corporate",
        "We'd like to arrange an investor dinner for 16 guests. Private room with AV facilities preferred.",
        RESOLVED_CORPORATE,
    ),
    (
        "corporate event unknown extraction",
        "frank@amazon.com",
        "unknown",
        "Team lunch for 20 people next Friday. We work at the London office.",
        RESOLVED_CORPORATE,
    ),
    (
        "corporate extraction with unknown domain",
        "grace@techstartup.io",
        "corporate",
        "We're hosting a company dinner for our team of 30 to celebrate our Series A raise.",
        RESOLVED_CORPORATE,
    ),
    (
        "corporate extraction at PWC",
        "henry@pwc.com",
        "corporate",
        "Business dinner for our senior managers — 14 people, private room, formal setting.",
        RESOLVED_CORPORATE,
    ),
    (
        "networking event at NHS",
        "iris@nhs.net",
        "corporate",
        "We're organising a networking dinner for 40 healthcare professionals.",
        RESOLVED_CORPORATE,
    ),
    (
        "company anniversary dinner at Apple",
        "jack@apple.com",
        "corporate",
        "Celebrating our company's 25th anniversary — dinner for 60 staff members.",
        RESOLVED_CORPORATE,
    ),
]

AGENCY_CASES = [
    (
        "venue find from known agency domain",
        "planner@eventconcepts.com",
        "unknown",
        "I'm sourcing a venue for a client dinner for 30 people on behalf of one of our corporate clients.",
        RESOLVED_AGENCY,
    ),
    (
        "commission request from agency domain",
        "alice@ashfield.co.uk",
        "agency",
        "We act as an event management agency and would like to discuss commission terms.",
        RESOLVED_AGENCY,
    ),
    (
        "RFP from unknown domain",
        "bob@corporateplanner.com",
        "unknown",
        "This is an RFP for a conference dinner for 80 delegates next March.",
        RESOLVED_AGENCY,
    ),
    (
        "site inspection from agency keyword domain",
        "carol@londonevents.co.uk",
        "agency",
        "We'd like to arrange a site visit for our client who is considering your venue.",
        RESOLVED_AGENCY,
    ),
    (
        "on behalf of client from gmail",
        "dave@gmail.com",
        "unknown",
        "I'm enquiring on behalf of our client who is looking for a private dining room for 25.",
        RESOLVED_AGENCY,
    ),
    (
        "my client birthday from consumer domain",
        "eve@hotmail.com",
        "agency",
        "I'm organising a birthday dinner for my client — she'd like the private room for 20.",
        RESOLVED_AGENCY,
    ),
    (
        "venue sourcing from events agency domain",
        "frank@premierhospitality.co.uk",
        "unknown",
        "We specialise in venue sourcing for corporate clients and are looking for options for a dinner.",
        RESOLVED_AGENCY,
    ),
    (
        "DDR from BCD meetings domain",
        "grace@bcd-meetings.com",
        "agency",
        "Looking for a DDR for 40 delegates — full day conference with working lunch.",
        RESOLVED_AGENCY,
    ),
    (
        "preferred supplier from agency domain",
        "henry@tripleseat.com",
        "corporate",
        "We are reaching out to discuss becoming a preferred supplier to your venue.",
        RESOLVED_AGENCY,
    ),
    (
        "delegate day rate from events keyword domain",
        "iris@conferenceplanning.co.uk",
        "unknown",
        "Enquiring about delegate day rates for a 2-day conference for 120 people.",
        RESOLVED_AGENCY,
    ),
]


# ── Dataset totals ─────────────────────────────────────────────────────────────

ALL_CASES = SOCIAL_CASES + CORPORATE_CASES + AGENCY_CASES
TOTAL_CASES = len(ALL_CASES)
SOCIAL_COUNT = len(SOCIAL_CASES)
CORPORATE_COUNT = len(CORPORATE_CASES)
AGENCY_COUNT = len(AGENCY_CASES)


# ── Individual case tests ─────────────────────────────────────────────────────


class TestSocialCases:
    @pytest.mark.parametrize("description,email,extraction,text,expected", SOCIAL_CASES)
    def test_social_case(self, description, email, extraction, text, expected):
        domain = SenderDomainClassificationService.classify(email)
        result = CustomerTypeResolver.resolve(extraction, domain, text)
        assert result.resolved_type == expected, (
            f"FAILED [{description}]: expected {expected}, got {result.resolved_type} "
            f"(method={result.resolution_method}, evidence={result.evidence})"
        )


class TestCorporateCases:
    @pytest.mark.parametrize("description,email,extraction,text,expected", CORPORATE_CASES)
    def test_corporate_case(self, description, email, extraction, text, expected):
        domain = SenderDomainClassificationService.classify(email)
        result = CustomerTypeResolver.resolve(extraction, domain, text)
        assert result.resolved_type == expected, (
            f"FAILED [{description}]: expected {expected}, got {result.resolved_type} "
            f"(method={result.resolution_method}, evidence={result.evidence})"
        )


class TestAgencyCases:
    @pytest.mark.parametrize("description,email,extraction,text,expected", AGENCY_CASES)
    def test_agency_case(self, description, email, extraction, text, expected):
        domain = SenderDomainClassificationService.classify(email)
        result = CustomerTypeResolver.resolve(extraction, domain, text)
        assert result.resolved_type == expected, (
            f"FAILED [{description}]: expected {expected}, got {result.resolved_type} "
            f"(method={result.resolution_method}, evidence={result.evidence})"
        )


# ── Accuracy metrics ──────────────────────────────────────────────────────────


class TestAccuracyMetrics:
    """Aggregate accuracy measurements across the full dataset.

    These tests verify that the resolver meets minimum accuracy thresholds.
    A failure here indicates a regression in classification logic.
    """

    @pytest.fixture(scope="class")
    def all_results(self):
        """Run resolver on all cases and return (expected, actual) pairs."""
        results = []
        for description, email, extraction, text, expected in ALL_CASES:
            domain = SenderDomainClassificationService.classify(email)
            result = CustomerTypeResolver.resolve(extraction, domain, text)
            results.append((expected, result.resolved_type, description, result.resolution_method))
        return results

    def test_overall_accuracy_meets_threshold(self, all_results):
        correct = sum(1 for exp, got, _, _ in all_results if exp == got)
        accuracy = correct / TOTAL_CASES
        failures = [
            f"  [{desc}]: expected {exp}, got {got} (method={method})"
            for exp, got, desc, method in all_results if exp != got
        ]
        failure_report = "\n".join(failures) if failures else "none"
        assert accuracy >= 0.95, (
            f"Overall accuracy {accuracy:.1%} below 95% threshold "
            f"({correct}/{TOTAL_CASES} correct).\nFailures:\n{failure_report}"
        )

    def test_false_agency_rate_below_threshold(self, all_results):
        """Non-agency cases should rarely be misclassified as agency."""
        non_agency = [(exp, got, desc, method) for exp, got, desc, method in all_results if exp != RESOLVED_AGENCY]
        false_agencies = [(exp, got, desc, method) for exp, got, desc, method in non_agency if got == RESOLVED_AGENCY]
        rate = len(false_agencies) / len(non_agency) if non_agency else 0.0
        failures = [
            f"  [{desc}]: expected {exp}, got {got} (method={method})"
            for exp, got, desc, method in false_agencies
        ]
        failure_report = "\n".join(failures) if failures else "none"
        assert rate <= 0.05, (
            f"False agency rate {rate:.1%} exceeds 5% threshold "
            f"({len(false_agencies)}/{len(non_agency)} non-agency cases mis-classified).\n"
            f"False positives:\n{failure_report}"
        )

    def test_false_corporate_rate_below_threshold(self, all_results):
        """Non-corporate cases should rarely be misclassified as corporate."""
        non_corporate = [(exp, got, desc, method) for exp, got, desc, method in all_results if exp != RESOLVED_CORPORATE]
        false_corporates = [(exp, got, desc, method) for exp, got, desc, method in non_corporate if got == RESOLVED_CORPORATE]
        rate = len(false_corporates) / len(non_corporate) if non_corporate else 0.0
        failures = [
            f"  [{desc}]: expected {exp}, got {got} (method={method})"
            for exp, got, desc, method in false_corporates
        ]
        failure_report = "\n".join(failures) if failures else "none"
        assert rate <= 0.05, (
            f"False corporate rate {rate:.1%} exceeds 5% threshold "
            f"({len(false_corporates)}/{len(non_corporate)} non-corporate cases mis-classified).\n"
            f"False positives:\n{failure_report}"
        )

    def test_social_recall_meets_threshold(self, all_results):
        """All social cases should be correctly identified."""
        social_cases = [(exp, got, desc, method) for exp, got, desc, method in all_results if exp == RESOLVED_SOCIAL]
        correct = sum(1 for exp, got, _, _ in social_cases if exp == got)
        recall = correct / len(social_cases) if social_cases else 0.0
        assert recall >= 0.90, (
            f"Social recall {recall:.1%} below 90% threshold ({correct}/{len(social_cases)})"
        )

    def test_corporate_recall_meets_threshold(self, all_results):
        """All corporate cases should be correctly identified."""
        corporate_cases = [(exp, got, desc, method) for exp, got, desc, method in all_results if exp == RESOLVED_CORPORATE]
        correct = sum(1 for exp, got, _, _ in corporate_cases if exp == got)
        recall = correct / len(corporate_cases) if corporate_cases else 0.0
        assert recall >= 0.90, (
            f"Corporate recall {recall:.1%} below 90% threshold ({correct}/{len(corporate_cases)})"
        )

    def test_agency_recall_meets_threshold(self, all_results):
        """All agency cases should be correctly identified."""
        agency_cases = [(exp, got, desc, method) for exp, got, desc, method in all_results if exp == RESOLVED_AGENCY]
        correct = sum(1 for exp, got, _, _ in agency_cases if exp == got)
        recall = correct / len(agency_cases) if agency_cases else 0.0
        assert recall >= 0.90, (
            f"Agency recall {recall:.1%} below 90% threshold ({correct}/{len(agency_cases)})"
        )

    def test_dataset_has_minimum_cases_per_type(self):
        assert SOCIAL_COUNT >= 5, "Need at least 5 social test cases"
        assert CORPORATE_COUNT >= 5, "Need at least 5 corporate test cases"
        assert AGENCY_COUNT >= 5, "Need at least 5 agency test cases"

    def test_no_llm_calls_in_resolver(self, all_results):
        """Verify test suite is fully deterministic."""
        import app.modules.enquiries.customer_type_resolver as mod
        source = open(mod.__file__).read()
        assert "AIGateway" not in source
