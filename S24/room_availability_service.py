from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
from peewee import DoesNotExist
from playhouse.shortcuts import model_to_dict

from models import Room, Event, RoomBlock, init_db
from pydantic_models import (
    RoomBlockCreate, RoomBlockUpdate, RoomBlockResponse,
    RoomCreate, RoomResponse,
    EventCreate, EventResponse
)
from logic import check_time_overlap, validate_datetime
app = FastAPI(
    title="Room Availability Service",
    description="Сервис занятости аудиторий",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/blocks/", response_model=RoomBlockResponse, status_code=201)
async def create_block(block: RoomBlockCreate):
    try:
        room = Room.get_by_id(block.room_id)
        event = Event.get_by_id(block.event_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Room или Event не найден")
    is_valid, error_msg = validate_datetime(block.start_datetime, block.end_datetime)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    if check_time_overlap(block.room_id, block.start_datetime, block.end_datetime):
        raise HTTPException(
            status_code=409, 
            detail="В это время аудитория уже занята"
        )
    new_block = RoomBlock.create(
        room=room,
        event=event,
        start_datetime=block.start_datetime,
        end_datetime=block.end_datetime,
        status=block.status,
        comment=block.comment
    )
    return RoomBlockResponse.model_validate(new_block)

@app.patch("/blocks/{block_id}", response_model=RoomBlockResponse)
async def update_block(block_id: int, block_data: RoomBlockUpdate):
    try:
        existing_block = RoomBlock.get_by_id(block_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    update_data = block_data.model_dump(exclude_unset=True)
    if 'start_datetime' in update_data or 'end_datetime' in update_data:
        start = update_data.get('start_datetime', existing_block.start_datetime)
        end = update_data.get('end_datetime', existing_block.end_datetime)
        
        is_valid, error_msg = validate_datetime(start, end)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        if check_time_overlap(existing_block.room_id, start, end, exclude_id=block_id):
            raise HTTPException(
                status_code=409,
                detail="В это время аудитория уже занята"
            )
    for field, value in update_data.items():
        setattr(existing_block, field, value)
    existing_block.save()
    return RoomBlockResponse.model_validate(existing_block)

@app.delete("/blocks/{block_id}")
async def delete_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    block.is_deleted = True
    block.save()
    return {"status_code": 200, "detail": "Блокировка удалена", "block_id": block_id}

@app.get("/blocks/{block_id}", response_model=RoomBlockResponse)
async def get_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)
        if block.is_deleted:
            raise HTTPException(status_code=404, detail="Блокировка не найдена")
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    return RoomBlockResponse.model_validate(block)

@app.get("/blocks/", response_model=List[RoomBlockResponse])
async def get_blocks(
    room_id: Optional[int] = Query(None, ge=1, description="ID аудитории"),
    event_id: Optional[int] = Query(None, ge=1, description="ID события"),
    status: Optional[str] = Query(None, pattern="^(active|cancelled|pending)$"),
    date_from: Optional[datetime] = Query(None, description="Начало диапазона"),
    date_to: Optional[datetime] = Query(None, description="Конец диапазона"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = RoomBlock.select().where(RoomBlock.is_deleted == False)
    if room_id:
        query = query.where(RoomBlock.room_id == room_id)
    if event_id:
        query = query.where(RoomBlock.event_id == event_id)
    if status:
        query = query.where(RoomBlock.status == status)
    if date_from:
        query = query.where(RoomBlock.start_datetime >= date_from)
    if date_to:
        query = query.where(RoomBlock.end_datetime <= date_to)
    query = query.order_by(RoomBlock.start_datetime).limit(limit).offset(offset)
    return [RoomBlockResponse.model_validate(block) for block in query]

@app.post("/rooms/", response_model=RoomResponse, status_code=201)
async def create_room(room: RoomCreate):
    try:
        existing = Room.get(Room.number == room.number)
        raise HTTPException(status_code=409, detail="Аудитория с таким номером уже существует")
    except DoesNotExist:
        new_room = Room.create(
            number=room.number,
            floor=room.floor,
            capacity=room.capacity
        )
        return RoomResponse.model_validate(new_room)

@app.get("/rooms/", response_model=List[RoomResponse])
async def get_rooms():
    return [RoomResponse.model_validate(room) for room in Room.select()]

@app.post("/events/", response_model=EventResponse, status_code=201)
async def create_event(event: EventCreate):
    new_event = Event.create(
        title=event.title,
        type=event.type
    )
    return EventResponse.model_validate(new_event)

@app.get("/events/", response_model=List[EventResponse])
async def get_events():
    return [EventResponse.model_validate(event) for event in Event.select()]

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Room Availability Service"}
