import uuid

from sqlalchemy.orm import Session

from app.modules.restaurants.models import Restaurant
from app.modules.restaurants.repository import RestaurantRepository
from app.modules.restaurants.schemas import RestaurantCreate, RestaurantUpdate


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
