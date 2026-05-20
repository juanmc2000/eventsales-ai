import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.personas.schemas import (
    PersonaCreate,
    PersonaListOut,
    PersonaOut,
    PersonaUpdate,
    RestaurantPersonaAssign,
    RestaurantPersonaOut,
)
from app.modules.personas.service import PersonaService

router = APIRouter(prefix="/api/v1/personas", tags=["personas"])


def get_service(db: Session = Depends(get_db)) -> PersonaService:
    return PersonaService(db)


@router.get("", response_model=PersonaListOut)
def list_personas(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: PersonaService = Depends(get_service),
) -> PersonaListOut:
    items, total = service.list_personas(skip=skip, limit=limit)
    return PersonaListOut(items=items, total=total)


@router.get("/{persona_id}", response_model=PersonaOut)
def get_persona(
    persona_id: uuid.UUID,
    service: PersonaService = Depends(get_service),
) -> PersonaOut:
    persona = service.get_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.post("", response_model=PersonaOut, status_code=201)
def create_persona(
    data: PersonaCreate,
    service: PersonaService = Depends(get_service),
) -> PersonaOut:
    try:
        return service.create_persona(data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{persona_id}", response_model=PersonaOut)
def update_persona(
    persona_id: uuid.UUID,
    data: PersonaUpdate,
    service: PersonaService = Depends(get_service),
) -> PersonaOut:
    persona = service.update_persona(persona_id, data)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.delete("/{persona_id}", response_model=PersonaOut)
def deactivate_persona(
    persona_id: uuid.UUID,
    service: PersonaService = Depends(get_service),
) -> PersonaOut:
    persona = service.deactivate_persona(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


# ── Restaurant persona assignments ────────────────────────────────────────────

restaurant_assignment_router = APIRouter(
    prefix="/api/v1/restaurants/{restaurant_id}/personas",
    tags=["restaurant-personas"],
)


@restaurant_assignment_router.get("", response_model=list[RestaurantPersonaOut])
def list_restaurant_personas(
    restaurant_id: uuid.UUID,
    service: PersonaService = Depends(get_service),
) -> list[RestaurantPersonaOut]:
    return service.list_restaurant_assignments(restaurant_id)


@restaurant_assignment_router.post("", response_model=RestaurantPersonaOut, status_code=201)
def assign_persona_to_restaurant(
    restaurant_id: uuid.UUID,
    data: RestaurantPersonaAssign,
    service: PersonaService = Depends(get_service),
) -> RestaurantPersonaOut:
    try:
        return service.assign_persona_to_restaurant(restaurant_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@restaurant_assignment_router.delete("/{persona_id}", status_code=204)
def remove_persona_from_restaurant(
    restaurant_id: uuid.UUID,
    persona_id: uuid.UUID,
    service: PersonaService = Depends(get_service),
) -> None:
    removed = service.remove_persona_from_restaurant(restaurant_id, persona_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Persona assignment not found")
