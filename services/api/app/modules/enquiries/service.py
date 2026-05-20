import uuid

from sqlalchemy.orm import Session

from app.modules.enquiries.models import Enquiry, EnquiryMessage
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.enquiries.schemas import (
    EnquiryCreate,
    EnquiryMessageCreate,
    EnquiryStatusUpdate,
    EnquiryUpdate,
)

VALID_STATUSES = {"new", "open", "proposal_sent", "follow_up", "confirmed", "cancelled", "lost"}


class EnquiryService:
    def __init__(self, db: Session) -> None:
        self._repo = EnquiryRepository(db)

    def list_enquiries(
        self,
        restaurant_id: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Enquiry], int]:
        items = self._repo.list(restaurant_id=restaurant_id, status=status, skip=skip, limit=limit)
        total = self._repo.count(restaurant_id=restaurant_id, status=status)
        return items, total

    def get_enquiry(self, enquiry_id: uuid.UUID) -> Enquiry | None:
        return self._repo.get_by_id(enquiry_id)

    def create_enquiry(self, data: EnquiryCreate) -> Enquiry:
        payload = data.model_dump()
        # Map budget_indication and other extra fields to metadata_ or notes
        # to avoid passing unknown columns to the ORM
        extra_fields = {"company_name", "budget_indication", "preferred_area", "dietary_requirements", "special_requests", "message"}
        notes_parts = []
        for field in extra_fields:
            val = payload.pop(field, None)
            if val:
                notes_parts.append(f"{field.replace('_', ' ').title()}: {val}")
        if notes_parts and not payload.get("notes"):
            payload["notes"] = "\n".join(notes_parts)
        # Map recommended_minimum_spend to metadata_
        rms = payload.pop("recommended_minimum_spend", None)
        if rms is not None:
            payload["metadata_"] = {"recommended_minimum_spend": rms}

        enquiry = self._repo.create(payload)

        # Add initial message if provided
        if data.message:
            self._repo.add_message(
                enquiry.id,
                {
                    "direction": "inbound",
                    "channel": data.source or "webform",
                    "body": data.message,
                },
            )

        return enquiry

    def update_enquiry_status(self, enquiry_id: uuid.UUID, data: EnquiryStatusUpdate) -> Enquiry | None:
        if data.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{data.status}'. Must be one of: {sorted(VALID_STATUSES)}")
        enquiry = self._repo.get_by_id(enquiry_id)
        if not enquiry:
            return None
        return self._repo.update(enquiry, {"status": data.status})

    def update_enquiry(self, enquiry_id: uuid.UUID, data: EnquiryUpdate) -> Enquiry | None:
        enquiry = self._repo.get_by_id(enquiry_id)
        if not enquiry:
            return None
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return enquiry
        return self._repo.update(enquiry, updates)

    def list_messages(self, enquiry_id: uuid.UUID) -> list[EnquiryMessage]:
        return self._repo.list_messages(enquiry_id)

    def add_message(self, enquiry_id: uuid.UUID, data: EnquiryMessageCreate) -> EnquiryMessage | None:
        enquiry = self._repo.get_by_id(enquiry_id)
        if not enquiry:
            return None
        return self._repo.add_message(enquiry_id, data.model_dump())
