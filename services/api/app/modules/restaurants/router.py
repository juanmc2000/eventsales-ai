import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.restaurants.schemas import (
    RestaurantCreate,
    RestaurantListOut,
    RestaurantOut,
    RestaurantUpdate,
)
from app.modules.restaurants.service import RestaurantService

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])


def get_service(db: Session = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


@router.get("", response_model=RestaurantListOut)
def list_restaurants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: RestaurantService = Depends(get_service),
) -> RestaurantListOut:
    items, total = service.list_restaurants(skip=skip, limit=limit)
    return RestaurantListOut(items=items, total=total)


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(
    restaurant_id: uuid.UUID,
    service: RestaurantService = Depends(get_service),
) -> RestaurantOut:
    restaurant = service.get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.post("", response_model=RestaurantOut, status_code=201)
def create_restaurant(
    data: RestaurantCreate,
    service: RestaurantService = Depends(get_service),
) -> RestaurantOut:
    try:
        return service.create_restaurant(data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{restaurant_id}", response_model=RestaurantOut)
def update_restaurant(
    restaurant_id: uuid.UUID,
    data: RestaurantUpdate,
    service: RestaurantService = Depends(get_service),
) -> RestaurantOut:
    restaurant = service.update_restaurant(restaurant_id, data)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.delete("/{restaurant_id}", response_model=RestaurantOut)
def deactivate_restaurant(
    restaurant_id: uuid.UUID,
    service: RestaurantService = Depends(get_service),
) -> RestaurantOut:
    restaurant = service.deactivate_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant
