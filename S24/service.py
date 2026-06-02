from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from peewee import DoesNotExist, IntegrityError
from pydantic import BaseModel, Field
from models import CANCELLED_STATUS_ID, Event, Room, RoomBlock, Status, db, init_db


def check_time_overlap(
    room_id: int,
    start: datetime,
    end: datetime,
    exclude_id: int = None,
) -> bool:
    return RoomBlock.has_time_overlap(room_id, start, end, exclude_id=exclude_id)


def validate_datetime(start: datetime, end: datetime, check_past: bool = True) -> tuple:
    if start >= end:
        return False, 'end_datetime должен быть позже start_datetime'
    if not RoomBlock.validate_not_past(start, check_past=check_past):
        return False, 'start_datetime не может быть в прошлом'
    return True, ''

class RoomCreate(BaseModel):
    number: str = Field(..., max_length=10)
    floor: int = Field(..., ge=0)
    capacity: int = Field(..., ge=1)


class RoomResponse(BaseModel):
    id: int
    number: str
    floor: int
    capacity: int

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    title: str = Field(..., max_length=100)
    type: str = Field(..., max_length=50)


class EventResponse(BaseModel):
    id: int
    title: str
    type: str

    class Config:
        from_attributes = True


class RoomBlockCreate(BaseModel):
    room_id: int = Field(..., ge=1)
    event_id: int = Field(..., ge=1)
    start_datetime: datetime
    end_datetime: datetime
    status_id: int = Field(default=1, ge=1)
    comment: str = Field(default="", max_length=500)
    is_deleted: bool = Field(default=False)


class RoomBlockUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status_id: Optional[int] = Field(None, ge=1)
    comment: Optional[str] = Field(None, max_length=500)
    is_deleted: Optional[bool] = None


class RoomBlockResponse(BaseModel):
    id: int
    room_id: int
    event_id: int
    start_datetime: datetime
    end_datetime: datetime
    status_id: int
    comment: str
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

app = FastAPI(
    title="Room Availability Service",
    description="Сервис занятости аудиторий",
    version="1.0.0",
)


@app.on_event("startup")
def startup_event():
    init_db()


@app.on_event("shutdown")
def shutdown_event():
    if not db.is_closed():
        db.close()


@app.post("/blocks/", response_model=RoomBlockResponse, status_code=201)
async def create_block(block: RoomBlockCreate):
    try:
        Room.get_by_id(block.room_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Room не найден")
    try:
        Event.get_by_id(block.event_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Event не найден")
    try:
        Status.get_by_id(block.status_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Status не найден")
    is_valid, error_msg = validate_datetime(block.start_datetime, block.end_datetime)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    if check_time_overlap(block.room_id, block.start_datetime, block.end_datetime):
        raise HTTPException(status_code=409, detail="В это время аудитория уже занята")
    try:
        new_block = RoomBlock.create(
            room_id=block.room_id,
            event_id=block.event_id,
            status_id=block.status_id,
            start_datetime=block.start_datetime,
            end_datetime=block.end_datetime,
            comment=block.comment,
            is_deleted=block.is_deleted,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Блокировка с такими room_id, start_datetime и end_datetime уже существует",
        )
    return RoomBlockResponse.model_validate(new_block)


@app.patch("/blocks/{block_id}", response_model=RoomBlockResponse)
async def update_block(block_id: int, block_data: RoomBlockUpdate):
    try:
        existing_block = RoomBlock.get_by_id(block_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    update_data = block_data.model_dump(exclude_unset=True)
    if 'status_id' in update_data:
        try:
            Status.get_by_id(update_data['status_id'])
        except DoesNotExist:
            raise HTTPException(status_code=404, detail='Status не найден')
    if 'start_datetime' in update_data or 'end_datetime' in update_data:
        start = update_data.get('start_datetime', existing_block.start_datetime)
        end = update_data.get('end_datetime', existing_block.end_datetime)
        check_past = 'start_datetime' in update_data
        is_valid, error_msg = validate_datetime(start, end, check_past=check_past)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        effective_status_id = update_data.get('status_id', getattr(existing_block, 'status_id_id', existing_block.status_id.id))
        if effective_status_id != CANCELLED_STATUS_ID and check_time_overlap(existing_block.room_id, start, end, exclude_id=block_id):
            raise HTTPException(status_code=409, detail="В это время аудитория уже занята")
    for field, value in update_data.items():
        setattr(existing_block, field, value)
    existing_block.save()
    return RoomBlockResponse.model_validate(existing_block)


@app.delete("/blocks/{block_id}")
async def delete_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)
    except DoesNotExist:
        return False
    if block.is_deleted:
        return False
    block.is_deleted = True
    block.save()
    return True


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
    room_id: Optional[int] = Query(None, ge=1),
    event_id: Optional[int] = Query(None, ge=1),
    status_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = RoomBlock.select().where(RoomBlock.is_deleted == False)
    if room_id:
        query = query.where(RoomBlock.room_id == room_id)
    if event_id:
        query = query.where(RoomBlock.event_id == event_id)
    if status_id:
        query = query.where(RoomBlock.status_id == status_id)
    if date_from and date_to:
        query = query.where(
            (RoomBlock.start_datetime < date_to) &
            (RoomBlock.end_datetime > date_from)
        )
    elif date_from:
        query = query.where(RoomBlock.end_datetime > date_from)
    elif date_to:
        query = query.where(RoomBlock.start_datetime < date_to)
    query = query.order_by(RoomBlock.start_datetime).limit(limit).offset(offset)
    return [RoomBlockResponse.model_validate(block) for block in query]


@app.post("/rooms/", response_model=RoomResponse, status_code=201)
async def create_room(room: RoomCreate):
    try:
        new_room = Room.create(
            number=room.number,
            floor=room.floor,
            capacity=room.capacity,
        )
        return RoomResponse.model_validate(new_room)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Аудитория с таким номером уже существует")


@app.get("/rooms/", response_model=List[RoomResponse])
async def get_rooms():
    return [RoomResponse.model_validate(room) for room in Room.select()]


@app.post("/events/", response_model=EventResponse, status_code=201)
async def create_event(event: EventCreate):
    new_event = Event.create(title=event.title, type=event.type)
    return EventResponse.model_validate(new_event)


@app.get("/events/", response_model=List[EventResponse])
async def get_events():
    return [EventResponse.model_validate(event) for event in Event.select()]


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Room Availability Service"}
