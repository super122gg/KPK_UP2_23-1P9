from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from peewee import DoesNotExist, IntegrityError
from pydantic import BaseModel, Field
from models import RoomBlock, Status, db, init_db



class RoomBlockCreate(BaseModel):
    room_id: int = Field(..., ge=1)
    event_id: int = Field(..., ge=1)
    start_datetime: datetime
    end_datetime: datetime
    status_id: int = Field(default=1, ge=1)
    comment: str = Field(default="", max_length=500)


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
    updated_at: datetime

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
        Status.get_by_id(block.status_id)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Status не найден")
    try:
        new_block = RoomBlock.create(
            room_id=block.room_id,
            event_id=block.event_id,
            status_id=block.status_id,
            start_datetime=block.start_datetime,
            end_datetime=block.end_datetime,
            comment=block.comment,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
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
    for field, value in update_data.items():
        setattr(existing_block, field, value)
    try:
        existing_block.save()
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Блокировка с такими room_id, start_datetime и end_datetime уже существует",
        )
    return RoomBlockResponse.model_validate(existing_block)


@app.delete("/blocks/{block_id}", status_code=200)
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
    if date_from or date_to:
        range_start = date_from if date_from else datetime.min
        range_end = date_to if date_to else datetime.max
        query = query.where(
            (RoomBlock.start_datetime < range_end) &
            (RoomBlock.end_datetime > range_start)
        )
    query = query.order_by(RoomBlock.start_datetime).limit(limit).offset(offset)
    return [RoomBlockResponse.model_validate(block) for block in query]


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Room Availability Service"}
