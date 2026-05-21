"""Enquiry intake orchestration service.

Coordinates webform-submitted enquiry creation:
1. Validates the target restaurant exists.
2. Resolves the default persona assigned to the restaurant.
3. Calculates a deterministic pricing recommendation.
4. Creates the enquiry record with persona and pricing context.
5. Creates an initial inbound message if a message body was provided.

No AI calls are made here — persona assignment and pricing are deterministic.
Draft response generation is handled by a separate service (AI-001).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.enquiries.models import Enquiry
from app.modules.enquiries.repository import EnquiryRepository
from app.modules.enquiries.schemas import EnquiryIntakeOut, WebformIntakeRequest
from app.modules.personas.models import Persona
from app.modules.personas.repository import PersonaRepository
from app.modules.pricing.repository import PricingRuleRepository
from app.modules.pricing.schemas import PricingRecommendationOut, PricingRecommendationRequest
from app.modules.pricing.service import PricingRuleService
from app.modules.restaurants.repository import RestaurantRepository


class EnquiryIntakeService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._enquiry_repo = EnquiryRepository(db)
        self._persona_repo = PersonaRepository(db)
        self._pricing_service = PricingRuleService(db)
        self._restaurant_repo = RestaurantRepository(db)

    def intake(self, request: WebformIntakeRequest) -> EnquiryIntakeOut:
        """Orchestrate webform enquiry intake and return enriched context."""

        # 1. Validate restaurant exists
        restaurant = self._restaurant_repo.get_by_id(request.restaurant_id)
        if not restaurant:
            raise ValueError(f"Restaurant {request.restaurant_id} not found.")

        # 2. Resolve default persona for the restaurant
        persona: Persona | None = self._persona_repo.get_default_persona_for_restaurant(
            request.restaurant_id
        )

        # 3. Calculate deterministic pricing recommendation
        day_of_week = (
            request.event_date.weekday()
            if request.event_date
            else datetime.now(tz=timezone.utc).weekday()
        )
        pricing: PricingRecommendationOut = self._pricing_service.calculate_recommendation(
            PricingRecommendationRequest(
                restaurant_id=request.restaurant_id,
                day_of_week=day_of_week,
                meal_period=request.meal_period,
                party_size=request.party_size,
            )
        )

        # 4. Build enquiry payload and persist
        notes_parts = []
        for field_name, label in [
            ("company_name", "Company"),
            ("budget_indication", "Budget Indication"),
            ("preferred_area", "Preferred Area"),
            ("dietary_requirements", "Dietary Requirements"),
            ("special_requests", "Special Requests"),
        ]:
            val = getattr(request, field_name, None)
            if val:
                notes_parts.append(f"{label}: {val}")

        enquiry_payload: dict = {
            "restaurant_id": request.restaurant_id,
            "persona_id": persona.id if persona else None,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "email": str(request.email),
            "phone": request.phone,
            "party_size": request.party_size,
            "event_date": request.event_date,
            "event_type": request.event_type,
            "source": "webform",
            "status": "new",
            "notes": "\n".join(notes_parts) if notes_parts else None,
            "metadata_": {"recommended_minimum_spend": pricing.recommended_minimum_spend},
        }

        enquiry: Enquiry = self._enquiry_repo.create(enquiry_payload)

        # 5. Create initial inbound message if guest provided one
        if request.message:
            self._enquiry_repo.add_message(
                enquiry.id,
                {
                    "direction": "inbound",
                    "channel": "webform",
                    "body": request.message,
                },
            )

        self._db.commit()

        return EnquiryIntakeOut(
            enquiry_id=enquiry.id,
            reference=enquiry.reference,
            status=enquiry.status,
            restaurant_id=enquiry.restaurant_id,
            persona_id=persona.id if persona else None,
            persona_name=persona.name if persona else None,
            recommended_minimum_spend=pricing.recommended_minimum_spend,
            pricing_explanation=pricing.explanation,
            created_at=enquiry.created_at,
        )
