from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from peewee import IntegrityError
from pydantic import BaseModel, Field

from models import RoomBlock, Status, StatusNotFoundError, db, init_db


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
        new_block = RoomBlock.create(
            room_id=block.room_id,
            event_id=block.event_id,
            status_id=block.status_id,
            start_datetime=block.start_datetime,
            end_datetime=block.end_datetime,
            comment=block.comment,
        )
    except StatusNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ошибка целостности данных")

    return RoomBlockResponse.model_validate(new_block)


@app.patch("/blocks/{block_id}", response_model=RoomBlockResponse)
async def update_block(block_id: int, block_data: RoomBlockUpdate):
    try:
        existing_block = RoomBlock.get_by_id(block_id)
        if existing_block.is_deleted:
            raise HTTPException(status_code=404, detail="Блокировка не найдена")
    except RoomBlock.DoesNotExist:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")

    update_data = block_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_block, field, value)

    try:
        existing_block.save()
    except StatusNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Ошибка целостности данных")

    return RoomBlockResponse.model_validate(existing_block)


@app.delete("/blocks/{block_id}", response_model=bool, status_code=200)
async def delete_block(block_id: int):
    return RoomBlock.soft_delete(block_id)


@app.get("/blocks/{block_id}", response_model=RoomBlockResponse)
async def get_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)
        if block.is_deleted:
            raise HTTPException(status_code=404, detail="Блокировка не найдена")
    except RoomBlock.DoesNotExist:
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

    if room_id is not None:
        query = query.where(RoomBlock.room_id == room_id)

    if event_id is not None:
        query = query.where(RoomBlock.event_id == event_id)

    if status_id is not None:
        query = query.where(RoomBlock.status_id == status_id)

    if date_from is not None and date_to is not None:
        query = query.where(
            (RoomBlock.start_datetime < date_to) &
            (RoomBlock.end_datetime > date_from)
        )
    elif date_from is not None:
        query = query.where(RoomBlock.end_datetime > date_from)
    elif date_to is not None:
        query = query.where(RoomBlock.start_datetime < date_to)

    return [
        RoomBlockResponse.model_validate(block)
        for block in query.limit(limit).offset(offset)
    ]


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Room Availability Service"
    }
