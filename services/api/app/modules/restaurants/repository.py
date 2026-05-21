import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.restaurants.models import Restaurant, Room


class RestaurantRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> list[Restaurant]:
        stmt = select(Restaurant)
        if active_only:
            stmt = stmt.where(Restaurant.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit).order_by(Restaurant.name)
        return list(self._db.scalars(stmt).all())

    def count(self, active_only: bool = True) -> int:
        stmt = select(Restaurant)
        if active_only:
            stmt = stmt.where(Restaurant.is_active.is_(True))
        return len(self._db.scalars(stmt).all())

    def get_by_id(self, restaurant_id: uuid.UUID) -> Restaurant | None:
        return self._db.get(Restaurant, restaurant_id)

    def get_by_slug(self, slug: str) -> Restaurant | None:
        stmt = select(Restaurant).where(Restaurant.slug == slug)
        return self._db.scalars(stmt).first()

    def create(self, data: dict[str, Any]) -> Restaurant:
        record = Restaurant(id=uuid.uuid4(), tenant_id="default", **data)
        self._db.add(record)
        self._db.flush()
        return record

    def update(self, restaurant: Restaurant, data: dict[str, Any]) -> Restaurant:
        for key, value in data.items():
            setattr(restaurant, key, value)
        self._db.flush()
        return restaurant

    def deactivate(self, restaurant: Restaurant) -> Restaurant:
        restaurant.is_active = False
        self._db.flush()
        return restaurant


class RoomRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_restaurant(
        self,
        restaurant_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[Room]:
        stmt = select(Room).where(Room.restaurant_id == restaurant_id)
        if active_only:
            stmt = stmt.where(Room.is_active.is_(True))
        stmt = stmt.order_by(Room.display_order, Room.name)
        return list(self._db.scalars(stmt).all())

    def count_for_restaurant(
        self,
        restaurant_id: uuid.UUID,
        active_only: bool = True,
    ) -> int:
        stmt = select(Room).where(Room.restaurant_id == restaurant_id)
        if active_only:
            stmt = stmt.where(Room.is_active.is_(True))
        return len(self._db.scalars(stmt).all())

    def get_by_id(self, room_id: uuid.UUID) -> Room | None:
        return self._db.get(Room, room_id)

    def create(self, data: dict[str, Any]) -> Room:
        record = Room(id=uuid.uuid4(), tenant_id="default", **data)
        self._db.add(record)
        self._db.flush()
        return record

    def update(self, room: Room, data: dict[str, Any]) -> Room:
        for key, value in data.items():
            setattr(room, key, value)
        self._db.flush()
        return room

    def deactivate(self, room: Room) -> Room:
        room.is_active = False
        self._db.flush()
        return room
