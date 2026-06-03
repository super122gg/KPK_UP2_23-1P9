from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from peewee import DoesNotExist, IntegrityError
from pydantic import BaseModel, Field, field_validator

from models import RoomBlock, Status, db



class RoomBlockCreate(BaseModel):
    room_id: int = Field(..., ge=1)
    event_id: int = Field(..., ge=1)
    start_datetime: datetime
    end_datetime: datetime
    status_id: int = Field(default=1, ge=1)
    comment: str = Field(default="", max_length=500)

    @field_validator('start_datetime')
    def validate_start_not_past(cls, v):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError('start_datetime cannot be in the past')
        return v

    @field_validator('end_datetime')
    def validate_end_after_start(cls, v, info):
        start = info.data.get('start_datetime')
        if start and v <= start:
            raise ValueError('end_datetime must be greater than start_datetime')
        return v


class RoomBlockUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status_id: Optional[int] = Field(None, ge=1)
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator('start_datetime')
    def validate_start_not_past(cls, v):
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError('start_datetime cannot be in the past')
        return v

    @field_validator('end_datetime')
    def validate_end_after_start(cls, v, info):
        if v is not None:
            start = info.data.get('start_datetime')
            if start and v <= start:
                raise ValueError('end_datetime must be greater than start_datetime')
        return v


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


class StatusResponse(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        from_attributes = True


class DeleteResponse(BaseModel):
    success: bool


app = FastAPI(title="Room Availability Service", version="1.0.0")


@app.on_event("shutdown")
def shutdown():
    if not db.is_closed():
        db.close()


def to_response(block: RoomBlock) -> RoomBlockResponse:
    return RoomBlockResponse(
        id=block.id,
        room_id=block.room_id,
        event_id=block.event_id,
        start_datetime=block.start_datetime,
        end_datetime=block.end_datetime,
        status_id=block.status_id,
        comment=block.comment,
        is_deleted=block.is_deleted,
        created_at=block.created_at,
        updated_at=block.updated_at,
    )


@app.post("/blocks/", response_model=RoomBlockResponse, status_code=201)
async def create_block(block: RoomBlockCreate):
    try:
        Status.get_by_id(block.status_id)
    except DoesNotExist:
        raise HTTPException(404, "Status not found")

    try:
        new_block = RoomBlock.create(**block.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    except IntegrityError as e:
        raise HTTPException(409, "Data conflict (duplicate or overlap)")

    return to_response(new_block)


@app.patch("/blocks/{block_id}", response_model=RoomBlockResponse)
async def update_block(block_id: int, block_data: RoomBlockUpdate):
    try:
        block = RoomBlock.get_by_id(block_id)

        if block.is_deleted:
            raise HTTPException(404, "Block not found")
    except DoesNotExist:
        raise HTTPException(404, "Block not found")

    data = block_data.model_dump(exclude_unset=True)

    if "status_id" in data:
        try:
            Status.get_by_id(data["status_id"])
        except DoesNotExist:
            raise HTTPException(404, "Status not found")

    for k, v in data.items():
        setattr(block, k, v)

    try:
        block.save()
    except ValueError as e:
        raise HTTPException(400, str(e))
    except IntegrityError as e:
        raise HTTPException(409, "Data conflict")

    return to_response(block)


@app.delete("/blocks/{block_id}", response_model=DeleteResponse)
async def delete_block(block_id: int):
    result = RoomBlock.soft_delete(block_id)
    return DeleteResponse(success=result)


@app.get("/blocks/{block_id}", response_model=RoomBlockResponse)
async def get_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)
    except DoesNotExist:
        raise HTTPException(404, "Block not found")
    return to_response(block)


@app.get("/blocks/", response_model=List[RoomBlockResponse])
async def get_blocks(
    room_id: Optional[int] = Query(None, ge=1),
    event_id: Optional[int] = Query(None, ge=1),
    status_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = RoomBlock.select()

    if room_id:
        query = query.where(RoomBlock.room_id == room_id)

    if event_id:
        query = query.where(RoomBlock.event_id == event_id)

    if status_id:
        query = query.where(RoomBlock.status_id == status_id)

    if date_from and date_to:
        query = query.where(
            RoomBlock.start_datetime < date_to,
            RoomBlock.end_datetime > date_from
        )
    elif date_from:
        query = query.where(RoomBlock.end_datetime > date_from)
    elif date_to:
        query = query.where(RoomBlock.start_datetime < date_to)

    query = query.order_by(RoomBlock.id).limit(limit).offset(offset)

    return [to_response(b) for b in query]


@app.get("/statuses/", response_model=List[StatusResponse])
async def get_statuses():
    return list(Status.select())


@app.get("/statuses/{status_id}", response_model=StatusResponse)
async def get_status(status_id: int):
    try:
        status = Status.get_by_id(status_id)
    except DoesNotExist:
        raise HTTPException(404, "Status not found")
    return status


@app.get("/health")
async def health():
    return {"status": "ok"}
