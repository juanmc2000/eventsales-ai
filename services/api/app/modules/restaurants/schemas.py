import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class RestaurantBase(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    settings: dict | None = None


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    settings: dict | None = None


class RestaurantOut(RestaurantBase):
    id: uuid.UUID
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RestaurantListOut(BaseModel):
    items: list[RestaurantOut]
    total: int


# --- Room schemas ---


class RoomBase(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    room_type: str | None = Field(default=None, max_length=100)
    seated_capacity: int | None = None
    standing_capacity: int | None = None
    min_capacity: int | None = None
    max_capacity: int | None = None
    layouts: list | None = None
    amenities: list | None = None
    asset_links: list | None = None
    room_hire_fee: Decimal | None = None
    minimum_spend_notes: str | None = None
    suitability_notes: str | None = None
    booking_url: str | None = Field(default=None, max_length=500)
    is_private_dining: bool = False
    display_order: int = 0


class RoomCreate(RoomBase):
    restaurant_id: uuid.UUID


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    room_type: str | None = Field(default=None, max_length=100)
    seated_capacity: int | None = None
    standing_capacity: int | None = None
    min_capacity: int | None = None
    max_capacity: int | None = None
    layouts: list | None = None
    amenities: list | None = None
    asset_links: list | None = None
    room_hire_fee: Decimal | None = None
    minimum_spend_notes: str | None = None
    suitability_notes: str | None = None
    booking_url: str | None = Field(default=None, max_length=500)
    is_private_dining: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None


class RoomOut(RoomBase):
    id: uuid.UUID
    tenant_id: str
    restaurant_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoomListOut(BaseModel):
    items: list[RoomOut]
    total: int


# --- Restaurant AI context schemas ---


class PersonaContextOut(BaseModel):
    """Persona metadata for AI context — system_prompt is intentionally excluded."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    tone: str
    style: str
    is_default: bool

    model_config = {"from_attributes": True}


class PricingRuleContextOut(BaseModel):
    """Pricing rule summary for AI context."""

    name: str
    meal_period: str
    day_of_week: int | None
    minimum_spend: Decimal
    minimum_covers: int | None
    notes: str | None

    model_config = {"from_attributes": True}


class RoomContextOut(BaseModel):
    """Room summary for AI context."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    room_type: str | None
    seated_capacity: int | None
    standing_capacity: int | None
    min_capacity: int | None
    max_capacity: int | None
    layouts: list | None
    amenities: list | None
    asset_links: list | None
    room_hire_fee: Decimal | None
    minimum_spend_notes: str | None
    suitability_notes: str | None
    booking_url: str | None
    is_private_dining: bool
    display_order: int

    model_config = {"from_attributes": True}


class RestaurantContextOut(BaseModel):
    """Full venue context for AI draft generation and operational UI use."""

    id: uuid.UUID
    tenant_id: str
    name: str
    slug: str
    description: str | None
    address: str | None
    phone: str | None
    email: str | None
    # Personas (raw system_prompt excluded)
    personas: list[PersonaContextOut]
    default_persona: PersonaContextOut | None
    # Active rooms/PDRs
    rooms: list[RoomContextOut]
    # Active pricing rules summary
    pricing_rules: list[PricingRuleContextOut]

    model_config = {"from_attributes": True}
