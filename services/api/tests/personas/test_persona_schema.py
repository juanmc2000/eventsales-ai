"""Smoke tests for persona schemas (no DB required)."""

import pytest


def test_persona_create_schema_valid() -> None:
    from app.modules.personas.schemas import PersonaCreate

    p = PersonaCreate(name="Eleanor", slug="eleanor", tone="warm", style="formal", system_prompt="You are Eleanor.")
    assert p.name == "Eleanor"
    assert p.slug == "eleanor"


def test_persona_create_schema_invalid_slug() -> None:
    from pydantic import ValidationError

    from app.modules.personas.schemas import PersonaCreate

    with pytest.raises(ValidationError):
        PersonaCreate(name="Eleanor", slug="Eleanor With Caps")


def test_persona_update_excludes_none() -> None:
    from app.modules.personas.schemas import PersonaUpdate

    update = PersonaUpdate(tone="direct")
    dumped = update.model_dump(exclude_none=True)
    assert "tone" in dumped
    assert "name" not in dumped


def test_persona_list_out_schema() -> None:
    from app.modules.personas.schemas import PersonaListOut

    result = PersonaListOut(items=[], total=0)
    assert result.total == 0


def test_restaurant_persona_assign_defaults() -> None:
    import uuid

    from app.modules.personas.schemas import RestaurantPersonaAssign

    assign = RestaurantPersonaAssign(persona_id=uuid.uuid4())
    assert assign.is_default is False
