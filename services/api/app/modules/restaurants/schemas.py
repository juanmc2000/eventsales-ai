import uuid
from datetime import datetime

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
