from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.personas.models import Persona, RestaurantPersona


class PersonaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> list[Persona]:
        stmt = select(Persona)
        if active_only:
            stmt = stmt.where(Persona.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit).order_by(Persona.name)
        return list(self._db.scalars(stmt).all())

    def count(self, active_only: bool = True) -> int:
        stmt = select(Persona)
        if active_only:
            stmt = stmt.where(Persona.is_active.is_(True))
        return len(self._db.scalars(stmt).all())

    def get_by_id(self, persona_id: uuid.UUID) -> Persona | None:
        return self._db.get(Persona, persona_id)

    def get_by_slug(self, slug: str) -> Persona | None:
        stmt = select(Persona).where(Persona.slug == slug)
        return self._db.scalars(stmt).first()

    def create(self, data: dict[str, Any]) -> Persona:
        record = Persona(id=uuid.uuid4(), **data)
        self._db.add(record)
        self._db.flush()
        return record

    def update(self, persona: Persona, data: dict[str, Any]) -> Persona:
        for key, value in data.items():
            setattr(persona, key, value)
        self._db.flush()
        return persona

    def deactivate(self, persona: Persona) -> Persona:
        persona.is_active = False
        self._db.flush()
        return persona

    def get_assignment(self, restaurant_id: uuid.UUID, persona_id: uuid.UUID) -> RestaurantPersona | None:
        stmt = select(RestaurantPersona).where(
            RestaurantPersona.restaurant_id == restaurant_id,
            RestaurantPersona.persona_id == persona_id,
        )
        return self._db.scalars(stmt).first()

    def list_assignments_for_restaurant(self, restaurant_id: uuid.UUID) -> list[RestaurantPersona]:
        stmt = select(RestaurantPersona).where(
            RestaurantPersona.restaurant_id == restaurant_id
        )
        return list(self._db.scalars(stmt).all())

    def assign(self, restaurant_id: uuid.UUID, persona_id: uuid.UUID, is_default: bool) -> RestaurantPersona:
        record = RestaurantPersona(
            id=uuid.uuid4(),
            restaurant_id=restaurant_id,
            persona_id=persona_id,
            is_default=is_default,
        )
        self._db.add(record)
        self._db.flush()
        return record

    def get_default_persona_for_restaurant(self, restaurant_id: uuid.UUID) -> Persona | None:
        """Return the default active persona assigned to a restaurant, or None."""
        stmt = (
            select(Persona)
            .join(RestaurantPersona, RestaurantPersona.persona_id == Persona.id)
            .where(
                RestaurantPersona.restaurant_id == restaurant_id,
                RestaurantPersona.is_default.is_(True),
                Persona.is_active.is_(True),
            )
        )
        return self._db.scalars(stmt).first()

    def remove_assignment(self, assignment: RestaurantPersona) -> None:
        self._db.delete(assignment)
        self._db.flush()
