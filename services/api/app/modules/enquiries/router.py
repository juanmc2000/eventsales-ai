import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.enquiries.schemas import (
    EnquiryCreate,
    EnquiryListOut,
    EnquiryMessageCreate,
    EnquiryMessageOut,
    EnquiryOut,
    EnquiryStatusUpdate,
    EnquiryUpdate,
)
from app.modules.enquiries.service import EnquiryService

router = APIRouter(prefix="/api/v1/enquiries", tags=["enquiries"])


def get_service(db: Session = Depends(get_db)) -> EnquiryService:
    return EnquiryService(db)


@router.get("", response_model=EnquiryListOut)
def list_enquiries(
    restaurant_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: EnquiryService = Depends(get_service),
) -> EnquiryListOut:
    items, total = service.list_enquiries(
        restaurant_id=restaurant_id, status=status, skip=skip, limit=limit
    )
    return EnquiryListOut(items=items, total=total)


@router.get("/{enquiry_id}", response_model=EnquiryOut)
def get_enquiry(
    enquiry_id: uuid.UUID,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    enquiry = service.get_enquiry(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


@router.post("", response_model=EnquiryOut, status_code=201)
def create_enquiry(
    data: EnquiryCreate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    return service.create_enquiry(data)


@router.patch("/{enquiry_id}/status", response_model=EnquiryOut)
def update_enquiry_status(
    enquiry_id: uuid.UUID,
    data: EnquiryStatusUpdate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    try:
        enquiry = service.update_enquiry_status(enquiry_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


@router.patch("/{enquiry_id}", response_model=EnquiryOut)
def update_enquiry(
    enquiry_id: uuid.UUID,
    data: EnquiryUpdate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryOut:
    enquiry = service.update_enquiry(enquiry_id, data)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return enquiry


# ── Messages ──────────────────────────────────────────────────────────────────


@router.get("/{enquiry_id}/messages", response_model=list[EnquiryMessageOut])
def list_enquiry_messages(
    enquiry_id: uuid.UUID,
    service: EnquiryService = Depends(get_service),
) -> list[EnquiryMessageOut]:
    enquiry = service.get_enquiry(enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return service.list_messages(enquiry_id)


@router.post("/{enquiry_id}/messages", response_model=EnquiryMessageOut, status_code=201)
def add_enquiry_message(
    enquiry_id: uuid.UUID,
    data: EnquiryMessageCreate,
    service: EnquiryService = Depends(get_service),
) -> EnquiryMessageOut:
    message = service.add_message(enquiry_id, data)
    if not message:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return message
