import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.restaurants.models import Restaurant, Room
from app.modules.restaurants.repository import RestaurantRepository, RoomRepository
from app.modules.restaurants.schemas import (
    PersonaContextOut,
    PricingRuleContextOut,
    RestaurantContextOut,
    RestaurantCreate,
    RestaurantUpdate,
    RoomContextOut,
    RoomCreate,
    RoomUpdate,
)


class RestaurantService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = RestaurantRepository(db)

    def list_restaurants(self, skip: int = 0, limit: int = 100) -> tuple[list[Restaurant], int]:
        items = self._repo.list(skip=skip, limit=limit)
        total = self._repo.count()
        return items, total

    def get_restaurant(self, restaurant_id: uuid.UUID) -> Restaurant | None:
        return self._repo.get_by_id(restaurant_id)

    def create_restaurant(self, data: RestaurantCreate) -> Restaurant:
        existing = self._repo.get_by_slug(data.slug)
        if existing:
            raise ValueError(f"Restaurant with slug '{data.slug}' already exists.")
        return self._repo.create(data.model_dump())

    def update_restaurant(self, restaurant_id: uuid.UUID, data: RestaurantUpdate) -> Restaurant | None:
        restaurant = self._repo.get_by_id(restaurant_id)
        if not restaurant:
            return None
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return restaurant
        return self._repo.update(restaurant, updates)

    def deactivate_restaurant(self, restaurant_id: uuid.UUID) -> Restaurant | None:
        restaurant = self._repo.get_by_id(restaurant_id)
        if not restaurant:
            return None
        return self._repo.deactivate(restaurant)

    def get_restaurant_context(
        self, restaurant_id: uuid.UUID
    ) -> RestaurantContextOut | None:
        """Assemble full venue context for AI draft generation and operational UI.

        Returns None if the restaurant does not exist.
        System prompts are intentionally excluded from persona data.
        """
        from app.modules.personas.models import Persona, RestaurantPersona
        from app.modules.pricing.models import PricingRule

        restaurant = self._repo.get_by_id(restaurant_id)
        if not restaurant:
            return None

        # Load restaurant-persona assignments with persona data
        rp_stmt = (
            select(RestaurantPersona)
            .where(RestaurantPersona.restaurant_id == restaurant_id)
        )
        rp_rows = list(self._db.scalars(rp_stmt).all())

        persona_ids = [rp.persona_id for rp in rp_rows]
        is_default_by_persona_id = {rp.persona_id: rp.is_default for rp in rp_rows}

        personas_out: list[PersonaContextOut] = []
        default_persona: PersonaContextOut | None = None
        if persona_ids:
            persona_stmt = select(Persona).where(
                Persona.id.in_(persona_ids), Persona.is_active.is_(True)
            )
            for persona in self._db.scalars(persona_stmt).all():
                is_default = is_default_by_persona_id.get(persona.id, False)
                ctx = PersonaContextOut(
                    id=persona.id,
                    name=persona.name,
                    slug=persona.slug,
                    description=persona.description,
                    tone=persona.tone,
                    style=persona.style,
                    is_default=is_default,
                )
                personas_out.append(ctx)
                if is_default:
                    default_persona = ctx

        # Active rooms ordered by display_order
        room_repo = RoomRepository(self._db)
        rooms = room_repo.list_for_restaurant(restaurant_id, active_only=True)
        rooms_out = [RoomContextOut.model_validate(r) for r in rooms]

        # Active pricing rules
        pricing_stmt = (
            select(PricingRule)
            .where(
                PricingRule.restaurant_id == restaurant_id,
                PricingRule.is_active.is_(True),
            )
            .order_by(PricingRule.meal_period, PricingRule.day_of_week)
        )
        pricing_out = [
            PricingRuleContextOut.model_validate(pr)
            for pr in self._db.scalars(pricing_stmt).all()
        ]

        return RestaurantContextOut(
            id=restaurant.id,
            tenant_id=restaurant.tenant_id,
            name=restaurant.name,
            slug=restaurant.slug,
            description=restaurant.description,
            address=restaurant.address,
            phone=restaurant.phone,
            email=restaurant.email,
            personas=personas_out,
            default_persona=default_persona,
            rooms=rooms_out,
            pricing_rules=pricing_out,
        )


class RoomService:
    def __init__(self, db: Session) -> None:
        self._repo = RoomRepository(db)
        self._restaurant_repo = RestaurantRepository(db)

    def list_rooms(
        self,
        restaurant_id: uuid.UUID,
        active_only: bool = True,
    ) -> tuple[list[Room], int]:
        items = self._repo.list_for_restaurant(restaurant_id, active_only=active_only)
        total = self._repo.count_for_restaurant(restaurant_id, active_only=active_only)
        return items, total

    def get_room(self, restaurant_id: uuid.UUID, room_id: uuid.UUID) -> Room | None:
        room = self._repo.get_by_id(room_id)
        if room and room.restaurant_id != restaurant_id:
            return None
        return room

    def create_room(self, restaurant_id: uuid.UUID, data: RoomCreate) -> Room:
        restaurant = self._restaurant_repo.get_by_id(restaurant_id)
        if not restaurant:
            raise ValueError("Restaurant not found.")
        # Ensure restaurant_id in data matches the path parameter
        payload = data.model_dump()
        payload["restaurant_id"] = restaurant_id
        return self._repo.create(payload)

    def update_room(
        self,
        restaurant_id: uuid.UUID,
        room_id: uuid.UUID,
        data: RoomUpdate,
    ) -> Room | None:
        room = self.get_room(restaurant_id, room_id)
        if not room:
            return None
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return room
        return self._repo.update(room, updates)

    def deactivate_room(
        self,
        restaurant_id: uuid.UUID,
        room_id: uuid.UUID,
    ) -> Room | None:
        room = self.get_room(restaurant_id, room_id)
        if not room:
            return None
        return self._repo.deactivate(room)
