import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PersonaBase(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    tone: str = Field(default="professional", max_length=100)
    style: str = Field(default="concise", max_length=100)
    system_prompt: str = Field(default="")


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    tone: str | None = Field(default=None, max_length=100)
    style: str | None = Field(default=None, max_length=100)
    system_prompt: str | None = None


class PersonaOut(PersonaBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaListOut(BaseModel):
    items: list[PersonaOut]
    total: int


class RestaurantPersonaAssign(BaseModel):
    persona_id: uuid.UUID
    is_default: bool = False


class RestaurantPersonaOut(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    persona_id: uuid.UUID
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
