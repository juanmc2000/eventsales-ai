"""InboundEmailService — converts a parsed inbound email into an enquiry.

Called by the IMAP inbox reader (WORKFLOW-006 workers side, not yet wired).
Can also be called directly in tests or from a future Celery task.

Design rules:
- PostgreSQL is the source of truth — all state written to DB, not Redis.
- Idempotency: duplicate external_message_id is a no-op.
- Restaurant fallback: use the first active restaurant when routing is ambiguous.
- Extraction is intentionally simple — no LLM, no NLP, no attachments.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.email.models import EmailEvent
from app.modules.enquiries.models import Enquiry, EnquiryMessage
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.restaurants.repository import RestaurantRepository


# ── Input / output types ───────────────────────────────────────────────────────


@dataclass
class ParsedInboundEmail:
    """Structured representation of a parsed inbound email message."""

    sender_email: str
    subject: str
    body: str
    received_at: datetime
    # SMTP Message-ID header — used for idempotency
    external_message_id: str | None = None
    # Display name of the sender (optional)
    sender_name: str | None = None


@dataclass
class InboundProcessResult:
    """Result of processing one inbound email."""

    enquiry_reference: str | None
    enquiry_id: uuid.UUID | None
    # True when the message was already processed (duplicate)
    duplicate: bool = False
    # Short description of what happened
    action: str = ""


# ── Service ────────────────────────────────────────────────────────────────────


class InboundEmailService:
    """Processes a parsed inbound email and creates an enquiry record."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._enquiry_repo = EnquiryRepository(db)
        self._restaurant_repo = RestaurantRepository(db)

    # ── Public interface ───────────────────────────────────────────────────────

    def process(self, parsed: ParsedInboundEmail) -> InboundProcessResult:
        """
        Convert a parsed inbound email into an enquiry record.

        Returns an InboundProcessResult.  If the email was already processed
        (duplicate external_message_id), returns the original enquiry reference
        with duplicate=True and does not create new records.
        """
        # 1. Idempotency guard
        if parsed.external_message_id:
            existing = self._find_event_by_message_id(parsed.external_message_id)
            if existing is not None:
                return InboundProcessResult(
                    duplicate=True,
                    enquiry_id=existing.enquiry_id,
                    enquiry_reference=None,
                    action="duplicate — already processed",
                )

        # 2. Restaurant inference
        restaurant = self._infer_restaurant()
        if restaurant is None:
            raise ValueError(
                "No active restaurants found — cannot assign inbound email enquiry"
            )

        # 3. Parse sender name
        first_name, last_name = self._split_sender_name(parsed.sender_name)

        # 4. Create enquiry
        enquiry = self._enquiry_repo.create(
            {
                "restaurant_id": restaurant.id,
                "first_name": first_name,
                "last_name": last_name,
                "email": parsed.sender_email,
                "source": "email",
                "status": "new",
            }
        )

        # 5. Create inbound message
        self._enquiry_repo.add_message(
            enquiry.id,
            {
                "direction": "inbound",
                "channel": "email",
                "subject": parsed.subject[:500] if parsed.subject else None,
                "body": parsed.body,
                "sent_at": parsed.received_at,
            },
        )

        # 6. Log email event (received)
        email_event = EmailEvent(
            enquiry_id=enquiry.id,
            direction="inbound",
            status="received",
            from_address=parsed.sender_email,
            to_address="inbox",  # placeholder — actual to-address from IMAP header
            subject=parsed.subject[:500] if parsed.subject else "",
            body=parsed.body,
            message_id=parsed.external_message_id,
        )
        self._db.add(email_event)
        self._db.commit()
        self._db.refresh(enquiry)

        return InboundProcessResult(
            duplicate=False,
            enquiry_id=enquiry.id,
            enquiry_reference=enquiry.reference,
            action="created",
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _find_event_by_message_id(self, message_id: str) -> EmailEvent | None:
        """Return an existing EmailEvent that matches the given SMTP Message-ID."""
        stmt = select(EmailEvent).where(EmailEvent.message_id == message_id)
        return self._db.scalars(stmt).first()

    def _infer_restaurant(self):
        """Return the first active restaurant (POC fallback — no routing logic)."""
        results = self._restaurant_repo.list(active_only=True, limit=1)
        return results[0] if results else None

    @staticmethod
    def _split_sender_name(display_name: str | None) -> tuple[str, str]:
        """
        Split a display name like "Alice Smith" into (first, last).
        Falls back to ("Unknown", "") if name is absent.
        """
        if not display_name or not display_name.strip():
            return "Unknown", ""
        parts = display_name.strip().split(None, 1)
        return parts[0], parts[1] if len(parts) > 1 else ""
