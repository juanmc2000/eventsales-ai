import uuid

from sqlalchemy.orm import Session

from app.modules.personas.models import Persona, RestaurantPersona
from app.modules.personas.repository import PersonaRepository
from app.modules.personas.schemas import PersonaCreate, PersonaUpdate, RestaurantPersonaAssign


class PersonaService:
    def __init__(self, db: Session) -> None:
        self._repo = PersonaRepository(db)

    def list_personas(self, skip: int = 0, limit: int = 100) -> tuple[list[Persona], int]:
        items = self._repo.list(skip=skip, limit=limit)
        total = self._repo.count()
        return items, total

    def get_persona(self, persona_id: uuid.UUID) -> Persona | None:
        return self._repo.get_by_id(persona_id)

    def create_persona(self, data: PersonaCreate) -> Persona:
        existing = self._repo.get_by_slug(data.slug)
        if existing:
            raise ValueError(f"Persona with slug '{data.slug}' already exists.")
        return self._repo.create(data.model_dump())

    def update_persona(self, persona_id: uuid.UUID, data: PersonaUpdate) -> Persona | None:
        persona = self._repo.get_by_id(persona_id)
        if not persona:
            return None
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return persona
        return self._repo.update(persona, updates)

    def deactivate_persona(self, persona_id: uuid.UUID) -> Persona | None:
        persona = self._repo.get_by_id(persona_id)
        if not persona:
            return None
        return self._repo.deactivate(persona)

    def list_restaurant_assignments(self, restaurant_id: uuid.UUID) -> list[RestaurantPersona]:
        return self._repo.list_assignments_for_restaurant(restaurant_id)

    def assign_persona_to_restaurant(
        self, restaurant_id: uuid.UUID, data: RestaurantPersonaAssign
    ) -> RestaurantPersona:
        existing = self._repo.get_assignment(restaurant_id, data.persona_id)
        if existing:
            raise ValueError(
                f"Persona {data.persona_id} is already assigned to restaurant {restaurant_id}."
            )
        persona = self._repo.get_by_id(data.persona_id)
        if not persona:
            raise ValueError(f"Persona {data.persona_id} not found.")
        return self._repo.assign(restaurant_id, data.persona_id, data.is_default)

    def remove_persona_from_restaurant(
        self, restaurant_id: uuid.UUID, persona_id: uuid.UUID
    ) -> bool:
        assignment = self._repo.get_assignment(restaurant_id, persona_id)
        if not assignment:
            return False
        self._repo.remove_assignment(assignment)
        return True
