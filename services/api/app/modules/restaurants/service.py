import uuid

from sqlalchemy.orm import Session

from app.modules.restaurants.models import Restaurant, Room
from app.modules.restaurants.repository import RestaurantRepository, RoomRepository
from app.modules.restaurants.schemas import (
    RestaurantCreate,
    RestaurantUpdate,
    RoomCreate,
    RoomUpdate,
)


class RestaurantService:
    def __init__(self, db: Session) -> None:
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
