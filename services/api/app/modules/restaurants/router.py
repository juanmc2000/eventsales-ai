import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.restaurants.schemas import (
    RestaurantContextOut,
    RestaurantCreate,
    RestaurantListOut,
    RestaurantOut,
    RestaurantUpdate,
    RoomCreate,
    RoomListOut,
    RoomOut,
    RoomUpdate,
)
from app.modules.restaurants.service import RestaurantService, RoomService

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])


def get_service(db: Session = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


def get_room_service(db: Session = Depends(get_db)) -> RoomService:
    return RoomService(db)


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


@router.get("/{restaurant_id}/context", response_model=RestaurantContextOut)
def get_restaurant_context(
    restaurant_id: uuid.UUID,
    service: RestaurantService = Depends(get_service),
) -> RestaurantContextOut:
    context = service.get_restaurant_context(restaurant_id)
    if not context:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return context


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


# --- Room endpoints ---


@router.get("/{restaurant_id}/rooms", response_model=RoomListOut)
def list_rooms(
    restaurant_id: uuid.UUID,
    active_only: bool = Query(default=True),
    service: RoomService = Depends(get_room_service),
) -> RoomListOut:
    items, total = service.list_rooms(restaurant_id, active_only=active_only)
    return RoomListOut(items=items, total=total)


@router.post("/{restaurant_id}/rooms", response_model=RoomOut, status_code=201)
def create_room(
    restaurant_id: uuid.UUID,
    data: RoomCreate,
    service: RoomService = Depends(get_room_service),
) -> RoomOut:
    try:
        return service.create_room(restaurant_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{restaurant_id}/rooms/{room_id}", response_model=RoomOut)
def get_room(
    restaurant_id: uuid.UUID,
    room_id: uuid.UUID,
    service: RoomService = Depends(get_room_service),
) -> RoomOut:
    room = service.get_room(restaurant_id, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.patch("/{restaurant_id}/rooms/{room_id}", response_model=RoomOut)
def update_room(
    restaurant_id: uuid.UUID,
    room_id: uuid.UUID,
    data: RoomUpdate,
    service: RoomService = Depends(get_room_service),
) -> RoomOut:
    room = service.update_room(restaurant_id, room_id, data)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.delete("/{restaurant_id}/rooms/{room_id}", response_model=RoomOut)
def deactivate_room(
    restaurant_id: uuid.UUID,
    room_id: uuid.UUID,
    service: RoomService = Depends(get_room_service),
) -> RoomOut:
    room = service.deactivate_room(restaurant_id, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room
