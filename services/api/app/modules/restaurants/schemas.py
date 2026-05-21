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
