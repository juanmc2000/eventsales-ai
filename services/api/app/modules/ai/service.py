"""Draft generation service.

Orchestrates context assembly, LLM provider selection, draft generation,
and persistence of the draft as an outbound EnquiryMessage.

Responsibilities:
- Load enquiry, persona, and restaurant from the database.
- Assemble DraftContext from the loaded records.
- Select the appropriate LLM provider (Anthropic or Fallback).
- Generate the draft body.
- Persist the draft as an outbound 'draft' channel EnquiryMessage.
- Return a DraftGenerationResult to the caller.

The raw prompt is never returned or stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.ai.provider import make_provider
from app.modules.ai.schemas import DraftContext, DraftGenerationResult
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.personas.repository import PersonaRepository
from app.modules.restaurants.repository import RestaurantRepository, RoomRepository


class DraftGenerationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._enquiry_repo = EnquiryRepository(db)
        self._persona_repo = PersonaRepository(db)
        self._restaurant_repo = RestaurantRepository(db)
        self._room_repo = RoomRepository(db)

    def generate_draft(self, enquiry_id: uuid.UUID) -> DraftGenerationResult:
        """Generate and store a persona-based draft response for an enquiry.

        Raises ValueError if the enquiry does not exist.
        """
        enquiry = self._enquiry_repo.get_by_id(enquiry_id)
        if not enquiry:
            raise ValueError(f"Enquiry {enquiry_id} not found.")

        # Load restaurant
        restaurant = self._restaurant_repo.get_by_id(enquiry.restaurant_id)
        restaurant_name = restaurant.name if restaurant else "our venue"
        restaurant_description = restaurant.description if restaurant else None
        restaurant_address = restaurant.address if restaurant else None

        # Load persona (from enquiry assignment, or fall back to restaurant default)
        persona = None
        if enquiry.persona_id:
            persona = self._persona_repo.get_by_id(enquiry.persona_id)
        if not persona:
            persona = self._persona_repo.get_default_persona_for_restaurant(
                enquiry.restaurant_id
            )

        persona_name = persona.name if persona else "Events Team"
        persona_tone = persona.tone if persona else "professional"
        persona_style = persona.style if persona else "concise"
        persona_system_prompt = persona.system_prompt if persona else ""

        # Extract recommended minimum spend from enquiry metadata
        recommended_minimum_spend: float | None = None
        if enquiry.metadata_ and isinstance(enquiry.metadata_, dict):
            raw = enquiry.metadata_.get("recommended_minimum_spend")
            if raw is not None:
                try:
                    recommended_minimum_spend = float(raw)
                except (TypeError, ValueError):
                    pass

        # Extract guest's initial message from stored notes or first inbound message
        guest_message = _extract_guest_message(enquiry.notes)

        # Match a suitable room/PDR deterministically
        preferred_area = getattr(enquiry, "preferred_area", None)
        room = _match_room(
            rooms=self._room_repo.list_for_restaurant(
                enquiry.restaurant_id, active_only=True
            ),
            party_size=enquiry.party_size,
            preferred_area=preferred_area,
        )

        context = DraftContext(
            enquiry_id=enquiry_id,
            guest_first_name=enquiry.first_name,
            guest_last_name=enquiry.last_name,
            event_type=enquiry.event_type,
            event_date=str(enquiry.event_date) if enquiry.event_date else None,
            party_size=enquiry.party_size,
            guest_message=guest_message,
            restaurant_name=restaurant_name,
            restaurant_description=restaurant_description,
            persona_name=persona_name,
            persona_tone=persona_tone,
            persona_style=persona_style,
            persona_system_prompt=persona_system_prompt,
            recommended_minimum_spend=recommended_minimum_spend,
            restaurant_address=restaurant_address,
            room_name=room.name if room else None,
            room_type=room.room_type if room else None,
            room_seated_capacity=room.seated_capacity if room else None,
            room_standing_capacity=room.standing_capacity if room else None,
            room_layouts=list(room.layouts) if room and room.layouts else None,
            room_amenities=list(room.amenities) if room and room.amenities else None,
            room_suitability_notes=room.suitability_notes if room else None,
            room_booking_url=room.booking_url if room else None,
            room_is_private_dining=room.is_private_dining if room else False,
        )

        # Select provider based on configured API key
        provider, is_fallback = make_provider(settings.anthropic_api_key)
        draft_body = provider.generate(context)

        subject = _build_subject(enquiry.first_name, enquiry.last_name, enquiry.event_type)

        # Persist draft as an outbound message so it appears in the message thread
        message = self._enquiry_repo.add_message(
            enquiry_id,
            {
                "direction": "outbound",
                "channel": "draft",
                "subject": subject,
                "body": draft_body,
                "sent_at": None,  # Draft — not yet sent
            },
        )
        self._db.commit()

        return DraftGenerationResult(
            enquiry_id=enquiry_id,
            message_id=message.id,
            subject=subject,
            body=draft_body,
            persona_name=persona_name,
            is_fallback=is_fallback,
            model=provider.model_name,
        )


# ── Internal helpers ───────────────────────────────────────────────────────────


def _extract_guest_message(notes: str | None) -> str | None:
    """Pull the guest's initial message text out of the enquiry notes string.

    The intake service stores extra fields as 'Label: value' lines in notes.
    We skip those label lines and look for longer prose that represents the
    guest's free-text message.
    """
    if not notes:
        return None
    lines = notes.strip().splitlines()
    prose_lines = [
        line for line in lines
        if line.strip() and ":" not in line[:40]
    ]
    return " ".join(prose_lines).strip() or None


def _build_subject(first_name: str, last_name: str, event_type: str | None) -> str:
    type_label = event_type.replace("_", " ").title() if event_type else "Event"
    return f"Re: {type_label} Enquiry — {first_name} {last_name}"


def _match_room(rooms: list, party_size: int | None, preferred_area: str | None) -> object | None:
    """Select the most suitable room deterministically.

    Priority:
    1. If preferred_area is set, find a room whose name contains that string (case-insensitive).
    2. Find the first room whose min_capacity <= party_size <= max_capacity, ordered by display_order.
    3. Fall back to the first active room by display_order.
    4. If no rooms exist, return None.

    This is intentionally simple — no ML, no availability checking.
    """
    if not rooms:
        return None

    # 1. Preferred area / name match
    if preferred_area:
        term = preferred_area.strip().lower()
        for room in rooms:
            if term in room.name.lower():
                return room

    # 2. Capacity match
    if party_size is not None:
        for room in rooms:
            min_cap = room.min_capacity or 1
            max_cap = room.max_capacity or room.seated_capacity or 0
            if max_cap and min_cap <= party_size <= max_cap:
                return room

    # 3. First room
    return rooms[0]
