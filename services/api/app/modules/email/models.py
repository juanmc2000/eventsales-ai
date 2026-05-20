import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.enquiries.models import Enquiry


class EmailEvent(Base):
    """A record of an email send or receive event.

    All email activity is logged here, whether sent via Gmail SMTP or
    received via IMAP inbox reading.  This is the PostgreSQL source of truth
    for email activity — not Redis.
    """

    __tablename__ = "email_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Optional: link to the enquiry this email relates to
    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # inbound (received) or outbound (sent)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # pending / sent / received / failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SMTP/IMAP message-id header for deduplication
    message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    # Error message if status == 'failed'
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Flexible metadata (SMTP headers, IMAP flags, etc.)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    enquiry: Mapped["Enquiry | None"] = relationship(
        "Enquiry", back_populates="email_events"
    )
