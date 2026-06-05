from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.enquiries.models import Enquiry, EnquiryMessage, EnquiryResponsePlan

# Lazy imports for models added in DATA-019
try:
    from app.modules.enquiries.models import EnquiryDateRequest, EnquiryCandidateDate
    _DATE_MODELS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DATE_MODELS_AVAILABLE = False
    EnquiryDateRequest = None  # type: ignore[assignment,misc]
    EnquiryCandidateDate = None  # type: ignore[assignment,misc]


class EnquiryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def generate_reference(self) -> str:
        """Generate a human-readable enquiry reference, e.g. ENQ-2026-0042."""
        year = datetime.now(tz=timezone.utc).year
        count = self._db.query(Enquiry).count()
        return f"ENQ-{year}-{count + 1:04d}"

    def list(
        self,
        restaurant_id: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Enquiry]:
        stmt = select(Enquiry)
        if restaurant_id:
            stmt = stmt.where(Enquiry.restaurant_id == restaurant_id)
        if status:
            stmt = stmt.where(Enquiry.status == status)
        stmt = stmt.order_by(Enquiry.created_at.desc()).offset(skip).limit(limit)
        return list(self._db.scalars(stmt).all())

    def count(
        self,
        restaurant_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> int:
        return len(self.list(restaurant_id=restaurant_id, status=status, skip=0, limit=100000))

    def get_by_id(self, enquiry_id: uuid.UUID) -> Enquiry | None:
        return self._db.get(Enquiry, enquiry_id)

    def get_by_reference(self, reference: str) -> Enquiry | None:
        stmt = select(Enquiry).where(Enquiry.reference == reference)
        return self._db.scalars(stmt).first()

    def create(self, data: dict[str, Any]) -> Enquiry:
        ref = self.generate_reference()
        record = Enquiry(id=uuid.uuid4(), reference=ref, **data)
        self._db.add(record)
        self._db.flush()
        return record

    def update(self, enquiry: Enquiry, data: dict[str, Any]) -> Enquiry:
        for key, value in data.items():
            setattr(enquiry, key, value)
        self._db.flush()
        return enquiry

    def list_messages(self, enquiry_id: uuid.UUID) -> list[EnquiryMessage]:
        stmt = (
            select(EnquiryMessage)
            .where(EnquiryMessage.enquiry_id == enquiry_id)
            .order_by(EnquiryMessage.created_at)
        )
        return list(self._db.scalars(stmt).all())

    def add_message(self, enquiry_id: uuid.UUID, data: dict[str, Any]) -> EnquiryMessage:
        record = EnquiryMessage(id=uuid.uuid4(), enquiry_id=enquiry_id, **data)
        self._db.add(record)
        self._db.flush()
        return record

    def get_latest_draft_message(self, enquiry_id: uuid.UUID) -> EnquiryMessage | None:
        """Return the most recently created outbound draft message for an enquiry."""
        stmt = (
            select(EnquiryMessage)
            .where(
                EnquiryMessage.enquiry_id == enquiry_id,
                EnquiryMessage.direction == "outbound",
                EnquiryMessage.channel == "draft",
            )
            .order_by(EnquiryMessage.created_at.desc())
            .limit(1)
        )
        return self._db.scalars(stmt).first()


class DateRequestRepository:
    """Read/write access for EnquiryDateRequest and EnquiryCandidateDate rows."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_latest_date_request(self, enquiry_id: uuid.UUID):
        """Return the most recently created EnquiryDateRequest for an enquiry, or None."""
        if not _DATE_MODELS_AVAILABLE or EnquiryDateRequest is None:
            return None
        stmt = (
            select(EnquiryDateRequest)
            .where(EnquiryDateRequest.enquiry_id == enquiry_id)
            .order_by(EnquiryDateRequest.created_at.desc())
            .limit(1)
        )
        return self._db.scalars(stmt).first()

    def list_candidate_dates(self, enquiry_id: uuid.UUID) -> list:
        """Return all EnquiryCandidateDate rows for an enquiry ordered by candidate_date."""
        if not _DATE_MODELS_AVAILABLE or EnquiryCandidateDate is None:
            return []
        stmt = (
            select(EnquiryCandidateDate)
            .where(EnquiryCandidateDate.enquiry_id == enquiry_id)
            .order_by(EnquiryCandidateDate.candidate_date)
        )
        return list(self._db.scalars(stmt).all())

    def list_candidate_dates_for_request(self, date_request_id: uuid.UUID) -> list:
        """Return all candidate dates for a specific date_request row."""
        if not _DATE_MODELS_AVAILABLE or EnquiryCandidateDate is None:
            return []
        stmt = (
            select(EnquiryCandidateDate)
            .where(EnquiryCandidateDate.date_request_id == date_request_id)
            .order_by(EnquiryCandidateDate.candidate_date)
        )
        return list(self._db.scalars(stmt).all())

    def update_candidate_date(
        self,
        candidate: Any,
        availability_status: str | None,
        pricing_checked: bool,
        recommended_minimum_spend: float | None,
    ) -> None:
        """Update availability and pricing fields on an EnquiryCandidateDate row."""
        candidate.availability_status = availability_status
        candidate.pricing_checked = pricing_checked
        candidate.recommended_minimum_spend = recommended_minimum_spend
        self._db.flush()


class ResponsePlanRepository:
    """Read/write access for EnquiryResponsePlan rows (ORCH-006)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        enquiry_id: uuid.UUID,
        plan_data: dict[str, Any],
        snapshot_id: uuid.UUID | None = None,
        tenant_id: str | None = None,
    ) -> EnquiryResponsePlan:
        """Persist a new response plan row and return it."""
        record = EnquiryResponsePlan(
            id=uuid.uuid4(),
            enquiry_id=enquiry_id,
            snapshot_id=snapshot_id,
            tenant_id=tenant_id,
            **plan_data,
        )
        self._db.add(record)
        self._db.flush()
        return record

    def get_latest(self, enquiry_id: uuid.UUID) -> EnquiryResponsePlan | None:
        """Return the most recently created response plan for an enquiry, or None."""
        stmt = (
            select(EnquiryResponsePlan)
            .where(EnquiryResponsePlan.enquiry_id == enquiry_id)
            .order_by(EnquiryResponsePlan.created_at.desc())
            .limit(1)
        )
        return self._db.scalars(stmt).first()
