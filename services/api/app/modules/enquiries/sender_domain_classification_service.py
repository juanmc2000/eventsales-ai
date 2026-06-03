"""Sender Domain Classification Service (CUST-001).

Classifies email sender domains into audience evidence categories based on
deterministic domain pattern matching.

Outputs:
- agency:    domain belongs to an event-management or agency business
- corporate: domain belongs to a known corporate / business entity
- consumer:  domain belongs to a free consumer email provider
- unknown:   domain cannot be classified

No LLM calls are made. All classification is deterministic.

Usage::

    result = SenderDomainClassificationService.classify("alice@microsoft.com")
    # result.audience_type  → "corporate"
    # result.confidence     → 0.9
    # result.match_reason   → "known_corporate_domain"
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Audience type constants ────────────────────────────────────────────────────

AUDIENCE_AGENCY = "agency"
AUDIENCE_CORPORATE = "corporate"
AUDIENCE_CONSUMER = "consumer"
AUDIENCE_UNKNOWN = "unknown"

ALL_AUDIENCE_TYPES = {AUDIENCE_AGENCY, AUDIENCE_CORPORATE, AUDIENCE_CONSUMER, AUDIENCE_UNKNOWN}

# ── Match reason constants ─────────────────────────────────────────────────────

REASON_KNOWN_AGENCY_DOMAIN = "known_agency_domain"
REASON_AGENCY_KEYWORD = "agency_keyword_in_domain"
REASON_KNOWN_CORPORATE_DOMAIN = "known_corporate_domain"
REASON_CORPORATE_TLD = "corporate_tld_pattern"
REASON_KNOWN_CONSUMER_DOMAIN = "known_consumer_domain"
REASON_NO_MATCH = "no_match"

# ── Domain lists ──────────────────────────────────────────────────────────────
# Known agency domains (exact second-level domain match, case-insensitive)
_KNOWN_AGENCY_DOMAINS: frozenset[str] = frozenset({
    "ashfield.co.uk",
    "eventconcepts.com",
    "eventconcepts.co.uk",
    "confabulation.co.uk",
    "hamiltonagency.co.uk",
    "bcd-meetings.com",
    "cvent.com",
    "tripleseat.com",
    "bia.com",
    "eventsforce.com",
    "ibtm.com",
    "delegate-wrangler.com",
    "eventbrite.com",
    "maritz.com",
    "ovationtravel.com",
    "meetingsbooker.com",
    "atpi.com",
    "gsa.co.uk",
    "creativengagementgroup.com",
    "fwevents.co.uk",
    "firstlight.com",
    "smyle.co.uk",
    "igniteeventgroup.com",
    "spiro.com",
})

# Keywords that strongly indicate an event-management / corporate-events agency.
# Checked as substrings of the full domain (before the TLD).
_AGENCY_KEYWORDS: tuple[str, ...] = (
    "event",
    "events",
    "agency",
    "meetings",
    "conference",
    "incentive",
    "incentives",
    "hospitality",
    "delegate",
    "venue",
    "venues",
    "congress",
)

# Known large corporate / enterprise domains (exact second-level domain match)
_KNOWN_CORPORATE_DOMAINS: frozenset[str] = frozenset({
    "microsoft.com",
    "google.com",
    "amazon.com",
    "apple.com",
    "ibm.com",
    "oracle.com",
    "salesforce.com",
    "sap.com",
    "accenture.com",
    "deloitte.com",
    "pwc.com",
    "kpmg.com",
    "ey.com",
    "mckinsey.com",
    "bcg.com",
    "bain.com",
    "barclays.com",
    "hsbc.com",
    "lloydsbank.com",
    "natwest.com",
    "santander.com",
    "goldmansachs.com",
    "jpmorgan.com",
    "citibank.com",
    "ubs.com",
    "credit-suisse.com",
    "db.com",
    "deutsche-bank.com",
    "rbs.co.uk",
    "bp.com",
    "shell.com",
    "unilever.com",
    "nestle.com",
    "airbus.com",
    "boeing.com",
    "volkswagen.com",
    "bmw.com",
    "mercedes-benz.com",
    "tesco.com",
    "sainsburys.co.uk",
    "marksandspencer.com",
    "boots.com",
    "astrazeneca.com",
    "gsk.com",
    "pfizer.com",
    "novartis.com",
    "bt.com",
    "vodafone.com",
    "o2.com",
    "bbc.co.uk",
    "sky.com",
    "channel4.com",
    "itv.com",
    "nhs.net",
    "gov.uk",
    "parliament.uk",
    "mod.uk",
    "hmrc.gov.uk",
})

# Free consumer email providers (exact second-level domain match)
_KNOWN_CONSUMER_DOMAINS: frozenset[str] = frozenset({
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "hotmail.co.uk",
    "hotmail.fr",
    "hotmail.de",
    "hotmail.it",
    "hotmail.es",
    "outlook.com",
    "outlook.co.uk",
    "live.com",
    "live.co.uk",
    "msn.com",
    "yahoo.com",
    "yahoo.co.uk",
    "yahoo.fr",
    "yahoo.de",
    "yahoo.it",
    "yahoo.es",
    "yahoo.com.au",
    "ymail.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "aol.com",
    "aol.co.uk",
    "protonmail.com",
    "proton.me",
    "tutanota.com",
    "zoho.com",
    "mail.com",
    "gmx.com",
    "gmx.co.uk",
    "gmx.net",
    "fastmail.com",
    "hey.com",
    "pm.me",
    "btinternet.com",
    "sky.com",
    "ntlworld.com",
    "virgin.net",
    "virginmedia.com",
    "talktalk.net",
    "blueyonder.co.uk",
    "plusnet.com",
    "tiscali.co.uk",
    "wanadoo.co.uk",
    "btopenworld.com",
})


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class DomainClassificationResult:
    """Result of sender domain classification."""

    audience_type: str
    confidence: float
    match_reason: str
    domain: str


# ── Service ───────────────────────────────────────────────────────────────────


class SenderDomainClassificationService:
    """Classify a sender email domain into an audience evidence category.

    Classification is deterministic — no LLM calls are made.

    Precedence (highest confidence first):
    1. Known agency domain (exact match)     → agency,    confidence=0.95
    2. Agency keyword in domain name         → agency,    confidence=0.75
    3. Known corporate domain (exact match)  → corporate, confidence=0.90
    4. Known consumer domain (exact match)   → consumer,  confidence=0.95
    5. No match                              → unknown,   confidence=0.0
    """

    @classmethod
    def classify(cls, email: str | None) -> DomainClassificationResult:
        """Classify the domain of the given email address.

        Returns DomainClassificationResult.  When *email* is None, empty,
        or cannot be parsed, returns ``unknown`` with confidence 0.0.

        Args:
            email: Full email address, e.g. ``"alice@microsoft.com"``.

        Returns:
            DomainClassificationResult with audience_type and confidence.
        """
        domain = cls._extract_domain(email)
        if not domain:
            return DomainClassificationResult(
                audience_type=AUDIENCE_UNKNOWN,
                confidence=0.0,
                match_reason=REASON_NO_MATCH,
                domain="",
            )

        lower = domain.lower()

        # Rule 1 — exact known agency domain
        if lower in _KNOWN_AGENCY_DOMAINS:
            return DomainClassificationResult(
                audience_type=AUDIENCE_AGENCY,
                confidence=0.95,
                match_reason=REASON_KNOWN_AGENCY_DOMAIN,
                domain=lower,
            )

        # Rule 2 — agency keyword substring in the domain name (before TLD)
        domain_name = lower.split(".")[0] if "." in lower else lower
        if any(kw in domain_name for kw in _AGENCY_KEYWORDS):
            return DomainClassificationResult(
                audience_type=AUDIENCE_AGENCY,
                confidence=0.75,
                match_reason=REASON_AGENCY_KEYWORD,
                domain=lower,
            )

        # Rule 3 — exact known corporate domain
        if lower in _KNOWN_CORPORATE_DOMAINS:
            return DomainClassificationResult(
                audience_type=AUDIENCE_CORPORATE,
                confidence=0.90,
                match_reason=REASON_KNOWN_CORPORATE_DOMAIN,
                domain=lower,
            )

        # Rule 4 — exact known consumer domain
        if lower in _KNOWN_CONSUMER_DOMAINS:
            return DomainClassificationResult(
                audience_type=AUDIENCE_CONSUMER,
                confidence=0.95,
                match_reason=REASON_KNOWN_CONSUMER_DOMAIN,
                domain=lower,
            )

        # Rule 5 — no match
        return DomainClassificationResult(
            audience_type=AUDIENCE_UNKNOWN,
            confidence=0.0,
            match_reason=REASON_NO_MATCH,
            domain=lower,
        )

    @staticmethod
    def _extract_domain(email: str | None) -> str | None:
        """Extract the domain part from an email address.

        Returns None if the email is not parseable.
        """
        if not email or not email.strip():
            return None
        email = email.strip()
        if "@" not in email:
            return None
        parts = email.rsplit("@", 1)
        if len(parts) != 2 or not parts[1]:
            return None
        return parts[1].lower()
