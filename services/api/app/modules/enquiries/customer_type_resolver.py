"""Customer Type Resolver (CUST-002).

Determines the final audience type for an enquiry by combining deterministic
signals from multiple evidence sources.

Inputs:
- audience_type_from_extraction: raw audience classification from the LLM extraction
  (social | corporate | agency | unknown)
- domain_classification: DomainClassificationResult from SenderDomainClassificationService
- enquiry_text: free-text enquiry content (used for commission/agency signals)

Output:
- resolved_type: social | corporate | agency | unknown
- confidence: float between 0.0 and 1.0
- resolution_method: how the final type was determined
- evidence: list of signals that contributed to the decision

Deterministic precedence rules (highest to lowest):
  Rule 1 — Agency domain (known)              → agency    (confidence 0.95)
  Rule 2 — Commission/agency text signal      → agency    (confidence 0.85)
  Rule 2b — Corporate context text signal     → corporate (confidence 0.88)  [RESP-080]
  Rule 2c — Social context text signal        → social    (confidence 0.85)  [RESP-081]
  Rule 3 — Corporate domain (known)           → corporate (confidence 0.90)
  Rule 4 — Extraction says corporate          → corporate (confidence 0.75)
  Rule 5 — Consumer domain                   → social    (confidence 0.80)
  Rule 6 — Agency keyword domain             → agency    (confidence 0.70)
  Rule 7 — Extraction says social            → social    (confidence 0.65)
  Rule 8 — No deterministic signal           → unknown   (confidence 0.0)

Rules are evaluated in order — first match wins.

No LLM calls are made.

Usage::

    from app.modules.enquiries.customer_type_resolver import CustomerTypeResolver
    from app.modules.enquiries.sender_domain_classification_service import (
        SenderDomainClassificationService,
    )

    domain_result = SenderDomainClassificationService.classify(sender_email)
    resolved = CustomerTypeResolver.resolve(
        audience_type_from_extraction="unknown",
        domain_classification=domain_result,
        enquiry_text=freeform_text,
    )
    # resolved.resolved_type → "corporate"
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.enquiries.sender_domain_classification_service import (
    AUDIENCE_AGENCY,
    AUDIENCE_CONSUMER,
    AUDIENCE_CORPORATE,
    AUDIENCE_UNKNOWN,
    REASON_AGENCY_KEYWORD,
    REASON_KNOWN_AGENCY_DOMAIN,
    REASON_KNOWN_CONSUMER_DOMAIN,
    REASON_KNOWN_CORPORATE_DOMAIN,
    DomainClassificationResult,
)

# ── Resolution method constants ────────────────────────────────────────────────

METHOD_KNOWN_AGENCY_DOMAIN = "known_agency_domain"
METHOD_COMMISSION_TEXT_SIGNAL = "commission_text_signal"
METHOD_CORPORATE_CONTEXT_TEXT = "corporate_context_text_signal"
METHOD_SOCIAL_CONTEXT_TEXT = "social_context_text_signal"
METHOD_KNOWN_CORPORATE_DOMAIN = "known_corporate_domain"
METHOD_EXTRACTION_CORPORATE = "extraction_said_corporate"
METHOD_CONSUMER_DOMAIN_SOCIAL = "consumer_domain_infers_social"
METHOD_EXTRACTION_SOCIAL = "extraction_said_social"
METHOD_AGENCY_KEYWORD_DOMAIN = "agency_keyword_domain"
METHOD_NO_SIGNAL = "no_deterministic_signal"

# ── Output types ──────────────────────────────────────────────────────────────

RESOLVED_AGENCY = "agency"
RESOLVED_CORPORATE = "corporate"
RESOLVED_SOCIAL = "social"
RESOLVED_UNKNOWN = "unknown"

ALL_RESOLVED_TYPES = {RESOLVED_AGENCY, RESOLVED_CORPORATE, RESOLVED_SOCIAL, RESOLVED_UNKNOWN}

# ── Corporate context text signals (RESP-080) ─────────────────────────────────
# Keywords that indicate a corporate/professional booking context regardless of
# sender domain. These fire after agency text signals (Rule 2) so that genuine
# agency enquiries that also mention client dinners remain classified as agency.
_CORPORATE_CONTEXT_SIGNALS: tuple[str, ...] = (
    "board meeting",
    "client meeting",
    "client dinner",
    "client lunch",
    "client thank-you",
    "client thank you",
    "client workshop",
    "team meeting",
    "work team meal",
    "business breakfast",
    "corporate lunch",
    "corporate dinner",
    "pa booking",
    "ea booking",
    "managing director",
    "private office",
    "family office",
)

# ── Social context text signals (RESP-081) ─────────────────────────────────────
# Keywords that indicate an explicit personal/social occasion context regardless
# of sender domain. These fire after corporate context signals (Rule 2b) so that
# enquiries containing both (e.g. "client birthday dinner") remain corporate.
# Prevents personal occasions sent from corporate email addresses from being
# misclassified as corporate (Rule 3 / Rule 4 over-correction).
_SOCIAL_CONTEXT_SIGNALS: tuple[str, ...] = (
    "birthday",
    "baby shower",
    "baby naming",
    "hen party",
    "hen do",
    "stag party",
    "stag do",
    "engagement party",
    "leaving do",
    "leaving party",
    "flatmate",
    "christening",
    "graduation dinner",
    "graduation lunch",
    "graduation celebration",
    "wedding anniversary",
)

# ── Commission / agency text signals ─────────────────────────────────────────
# Keywords that strongly indicate this is an agency enquiry (commission intent,
# professional event-management language, etc.)
_COMMISSION_SIGNALS: tuple[str, ...] = (
    "commission",
    "agent fee",
    "agency fee",
    "fam trip",
    "familiarisation",
    "site visit",
    "site inspection",
    "rddr",
    "rddr commission",
    "on behalf of our client",
    "acting on behalf",
    "my client",
    "our client",
    "venue find",
    "venue search",
    "venue sourcing",
    "preferred supplier",
    "rfp",
    "request for proposal",
    "ddr",
    "delegate day rate",
)


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class CustomerTypeResolution:
    """Result of customer type resolution."""

    resolved_type: str
    confidence: float
    resolution_method: str
    evidence: list[str] = field(default_factory=list)


# ── Resolver ──────────────────────────────────────────────────────────────────


class CustomerTypeResolver:
    """Resolve final customer audience type from multiple deterministic signals.

    All resolution is deterministic — no LLM calls are made.
    """

    @classmethod
    def resolve(
        cls,
        audience_type_from_extraction: str | None,
        domain_classification: DomainClassificationResult | None,
        enquiry_text: str | None = None,
    ) -> CustomerTypeResolution:
        """Resolve the final audience type.

        Args:
            audience_type_from_extraction: Raw audience type from LLM extraction.
                Expected values: social | corporate | agency | unknown.
                None or unrecognised values are treated as ``unknown``.
            domain_classification: Classification result from
                SenderDomainClassificationService.classify(). May be None when
                no sender email is available.
            enquiry_text: Free-text enquiry message. Used to detect commission
                or agency-specific language. May be None.

        Returns:
            CustomerTypeResolution with resolved_type, confidence, resolution_method,
            and evidence list.
        """
        extraction_type = (audience_type_from_extraction or "unknown").lower().strip()
        domain_type = domain_classification.audience_type if domain_classification else AUDIENCE_UNKNOWN
        domain_reason = domain_classification.match_reason if domain_classification else ""
        text_lower = (enquiry_text or "").lower()

        evidence: list[str] = []

        # Rule 1 — Known agency domain (exact match, highest precedence)
        if domain_type == AUDIENCE_AGENCY and domain_reason == REASON_KNOWN_AGENCY_DOMAIN:
            evidence.append(f"sender domain classified as agency (known domain, confidence={domain_classification.confidence:.2f})")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_AGENCY,
                confidence=0.95,
                resolution_method=METHOD_KNOWN_AGENCY_DOMAIN,
                evidence=evidence,
            )

        # Rule 2 — Commission / agency-specific language in enquiry text
        triggered_signals = [sig for sig in _COMMISSION_SIGNALS if sig in text_lower]
        if triggered_signals:
            evidence.append(f"agency text signals detected: {triggered_signals}")
            if domain_type == AUDIENCE_AGENCY:
                evidence.append(f"domain also classified as agency ({domain_reason})")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_AGENCY,
                confidence=0.85,
                resolution_method=METHOD_COMMISSION_TEXT_SIGNAL,
                evidence=evidence,
            )

        # Rule 2b — Corporate context text signal (RESP-080)
        # Fires when the enquiry body contains explicit corporate-context keywords.
        # Takes precedence over consumer-domain social inference (Rule 5) but yields
        # to agency text signals (Rule 2) already checked above.
        triggered_corporate = [sig for sig in _CORPORATE_CONTEXT_SIGNALS if sig in text_lower]
        if triggered_corporate:
            evidence.append(f"corporate context signals detected in enquiry text: {triggered_corporate}")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_CORPORATE,
                confidence=0.88,
                resolution_method=METHOD_CORPORATE_CONTEXT_TEXT,
                evidence=evidence,
            )

        # Rule 2c — Social context text signal (RESP-081)
        # Fires when the enquiry body contains an explicit personal/social occasion
        # keyword (birthday, baby shower, flatmate, etc.). Takes precedence over
        # corporate domain (Rule 3) and extraction-says-corporate (Rule 4), preventing
        # personal occasions sent from corporate email addresses from being classified
        # as corporate. Yields to corporate context text (Rule 2b) already checked
        # above, so "client birthday dinner" remains corporate.
        triggered_social = [sig for sig in _SOCIAL_CONTEXT_SIGNALS if sig in text_lower]
        if triggered_social:
            evidence.append(f"social context signals detected in enquiry text: {triggered_social}")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_SOCIAL,
                confidence=0.85,
                resolution_method=METHOD_SOCIAL_CONTEXT_TEXT,
                evidence=evidence,
            )

        # Rule 3 — Known corporate domain
        if domain_type == AUDIENCE_CORPORATE and domain_reason == REASON_KNOWN_CORPORATE_DOMAIN:
            evidence.append(f"sender domain classified as corporate (known domain, confidence={domain_classification.confidence:.2f})")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_CORPORATE,
                confidence=0.90,
                resolution_method=METHOD_KNOWN_CORPORATE_DOMAIN,
                evidence=evidence,
            )

        # Rule 4 — Extraction classified as corporate (plus domain doesn't say otherwise)
        if extraction_type == "corporate" and domain_type not in (AUDIENCE_CONSUMER,):
            evidence.append("LLM extraction classified audience as corporate")
            if domain_type == AUDIENCE_CORPORATE:
                evidence.append("domain also appears corporate")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_CORPORATE,
                confidence=0.75,
                resolution_method=METHOD_EXTRACTION_CORPORATE,
                evidence=evidence,
            )

        # Rule 5 — Consumer domain implies social enquiry
        if domain_type == AUDIENCE_CONSUMER and domain_reason == REASON_KNOWN_CONSUMER_DOMAIN:
            evidence.append(f"sender domain classified as consumer (free email provider, confidence={domain_classification.confidence:.2f})")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_SOCIAL,
                confidence=0.80,
                resolution_method=METHOD_CONSUMER_DOMAIN_SOCIAL,
                evidence=evidence,
            )

        # Rule 6 — Agency keyword domain (higher confidence than LLM social extraction)
        if domain_type == AUDIENCE_AGENCY and domain_reason == REASON_AGENCY_KEYWORD:
            evidence.append(f"sender domain name contains agency keyword (confidence={domain_classification.confidence:.2f})")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_AGENCY,
                confidence=0.70,
                resolution_method=METHOD_AGENCY_KEYWORD_DOMAIN,
                evidence=evidence,
            )

        # Rule 7 — Extraction classified as social
        if extraction_type == "social":
            evidence.append("LLM extraction classified audience as social")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_SOCIAL,
                confidence=0.65,
                resolution_method=METHOD_EXTRACTION_SOCIAL,
                evidence=evidence,
            )

        # Rule 8 — No deterministic signal
        if extraction_type == "agency":
            # LLM said agency but no domain or text corroboration — lower confidence
            evidence.append("LLM extraction classified as agency but no domain or text corroboration")
            return CustomerTypeResolution(
                resolved_type=RESOLVED_AGENCY,
                confidence=0.50,
                resolution_method=METHOD_NO_SIGNAL,
                evidence=evidence,
            )

        evidence.append("no deterministic signal from domain or text; extraction type is unknown")
        return CustomerTypeResolution(
            resolved_type=RESOLVED_UNKNOWN,
            confidence=0.0,
            resolution_method=METHOD_NO_SIGNAL,
            evidence=evidence,
        )
