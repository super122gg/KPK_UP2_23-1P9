from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from peewee import DoesNotExist, IntegrityError
from pydantic import BaseModel, Field, field_validator

from models import RoomBlock, Status, db


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class RoomBlockCreate(BaseModel):
    room_id: int = Field(..., ge=1)
    event_id: int = Field(..., ge=1)
    start_datetime: datetime
    end_datetime: datetime
    status_id: int = Field(default=1, ge=1)
    comment: str = Field(default="", max_length=500)

    @field_validator("start_datetime")
    def validate_start_not_past(cls, v):
        v = to_utc(v)

        if v <= datetime.now(timezone.utc):
            raise ValueError(
                "start_datetime cannot be in the past"
            )

        return v

    @field_validator("end_datetime")
    def validate_end_after_start(cls, v, info):
        v = to_utc(v)

        start = info.data.get("start_datetime")

        if start and v <= start:
            raise ValueError(
                "end_datetime must be greater than start_datetime"
            )

        return v


class RoomBlockUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status_id: Optional[int] = Field(None, ge=1)
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator("start_datetime")
    def validate_start_not_past(cls, v):
        if v is not None:
            v = to_utc(v)

            if v <= datetime.now(timezone.utc):
                raise ValueError(
                    "start_datetime cannot be in the past"
                )

        return v

    @field_validator("end_datetime")
    def validate_end_after_start(cls, v, info):
        if v is not None:
            v = to_utc(v)

            start = info.data.get("start_datetime")

            if start and v <= start:
                raise ValueError(
                    "end_datetime must be greater than start_datetime"
                )

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


app = FastAPI(
    title="Room Availability Service",
    version="1.0.0"
)


@app.on_event("shutdown")
def shutdown():
    if not db.is_closed():
        db.close()


def to_response(block: RoomBlock):
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
        updated_at=block.updated_at
    )


def check_duplicate(
    room_id,
    start,
    end,
    exclude_id=None
):
    start_utc = to_utc(start)
    end_utc = to_utc(end)

    query = RoomBlock.select().where(
        (RoomBlock.is_deleted == False) &
        (RoomBlock.room_id == room_id) &
        (RoomBlock.start_datetime == start_utc) &
        (RoomBlock.end_datetime == end_utc)
    )

    if exclude_id:
        query = query.where(
            RoomBlock.id != exclude_id
        )

    return query.exists()


def check_overlap(
    room_id,
    start,
    end,
    exclude_id=None
):
    start_utc = to_utc(start)
    end_utc = to_utc(end)

    query = RoomBlock.select().where(
        (RoomBlock.is_deleted == False) &
        (RoomBlock.room_id == room_id) &
        (RoomBlock.status_id != Status.CANCELLED_STATUS_ID) &
        (RoomBlock.start_datetime < end_utc) &
        (RoomBlock.end_datetime > start_utc)
    )

    if exclude_id:
        query = query.where(
            RoomBlock.id != exclude_id
        )

    return query.exists()


@app.post(
    "/blocks/",
    response_model=RoomBlockResponse,
    status_code=201
)
async def create_block(block: RoomBlockCreate):
    try:
        Status.get_by_id(block.status_id)

        if check_duplicate(
            block.room_id,
            block.start_datetime,
            block.end_datetime
        ):
            raise HTTPException(
                409,
                "Duplicate block (room_id, start_datetime, end_datetime)"
            )

        if (
            block.status_id != Status.CANCELLED_STATUS_ID
            and
            check_overlap(
                block.room_id,
                block.start_datetime,
                block.end_datetime
            )
        ):
            raise HTTPException(
                409,
                "Time overlap with existing active block"
            )

        new_block = RoomBlock.create(
            **block.model_dump()
        )

        return to_response(new_block)

    except DoesNotExist:
        raise HTTPException(
            404,
            "Status not found"
        )

    except ValueError as e:
        raise HTTPException(
            400,
            str(e)
        )

    except IntegrityError:
        raise HTTPException(
            409,
            "Database conflict"
        )


@app.patch(
    "/blocks/{block_id}",
    response_model=RoomBlockResponse
)
async def update_block(
    block_id: int,
    block_data: RoomBlockUpdate
):
    try:
        block = RoomBlock.get_by_id(block_id)

        if block.is_deleted:
            raise HTTPException(
                404,
                "Block not found"
            )

        data = block_data.model_dump(
            exclude_unset=True
        )

        if "status_id" in data:
            try:
                Status.get_by_id(data["status_id"])
            except DoesNotExist:
                raise HTTPException(404, "Status not found")

        new_start = data.get(
            "start_datetime",
            block.start_datetime
        )

        new_end = data.get(
            "end_datetime",
            block.end_datetime
        )

        new_status = data.get(
            "status_id",
            block.status_id
        )

        if "start_datetime" in data or "end_datetime" in data:
            new_start_utc = to_utc(new_start)
            new_end_utc = to_utc(new_end)

            if new_end_utc <= new_start_utc:
                raise HTTPException(
                    400,
                    "end_datetime must be greater than start_datetime"
                )

            if "start_datetime" in data and new_start_utc <= datetime.now(timezone.utc):
                raise HTTPException(
                    400,
                    "start_datetime cannot be in the past"
                )

        if check_duplicate(
            block.room_id,
            new_start,
            new_end,
            block_id
        ):
            raise HTTPException(
                409,
                "Duplicate block (room_id, start_datetime, end_datetime)"
            )

        if (
            new_status != Status.CANCELLED_STATUS_ID
            and
            check_overlap(
                block.room_id,
                new_start,
                new_end,
                block_id
            )
        ):
            raise HTTPException(
                409,
                "Time overlap with existing active block"
            )

        for k, v in data.items():
            setattr(block, k, v)

        block.save()

        return to_response(block)

    except DoesNotExist:
        raise HTTPException(
            404,
            "Block not found"
        )

    except ValueError as e:
        raise HTTPException(
            400,
            str(e)
        )

    except IntegrityError:
        raise HTTPException(
            409,
            "Database conflict"
        )


@app.delete(
    "/blocks/{block_id}",
    response_model=DeleteResponse
)
async def delete_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)

        if block.is_deleted:
            return DeleteResponse(
                success=False
            )

        block.is_deleted = True
        block.save()

        return DeleteResponse(
            success=True
        )

    except DoesNotExist:
        return DeleteResponse(
            success=False
        )


@app.get(
    "/blocks/{block_id}",
    response_model=RoomBlockResponse
)
async def get_block(block_id: int):
    try:
        block = RoomBlock.get_by_id(block_id)
        return to_response(block)

    except DoesNotExist:
        raise HTTPException(
            404,
            "Block not found"
        )


@app.get(
    "/blocks/",
    response_model=List[RoomBlockResponse]
)
async def get_blocks(
    room_id: Optional[int] = Query(None, ge=1),
    event_id: Optional[int] = Query(None, ge=1),
    status_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    # Приводим date_from и date_to к UTC перед сравнением
    if date_from is not None:
        date_from_utc = to_utc(date_from)
    else:
        date_from_utc = None

    if date_to is not None:
        date_to_utc = to_utc(date_to)
    else:
        date_to_utc = None

    if date_from_utc is not None and date_to_utc is not None and date_from_utc >= date_to_utc:
        raise HTTPException(
            400,
            "date_from must be less than date_to"
        )

    query = RoomBlock.select()

    if room_id:
        query = query.where(
            RoomBlock.room_id == room_id
        )

    if event_id:
        query = query.where(
            RoomBlock.event_id == event_id
        )

    if status_id:
        query = query.where(
            RoomBlock.status_id == status_id
        )

    if date_from_utc and date_to_utc:
        query = query.where(
            RoomBlock.start_datetime < date_to_utc,
            RoomBlock.end_datetime > date_from_utc
        )

    elif date_from_utc:
        query = query.where(
            RoomBlock.end_datetime > date_from_utc
        )

    elif date_to_utc:
        query = query.where(
            RoomBlock.start_datetime < date_to_utc
        )

    query = query.order_by(
        RoomBlock.id
    ).limit(limit).offset(offset)

    return [
        to_response(item)
        for item in query
    ]


@app.get(
    "/statuses/",
    response_model=List[StatusResponse]
)
async def get_statuses():
    return [
        StatusResponse.model_validate(s)
        for s in Status.select()
    ]


@app.get(
    "/statuses/{status_id}",
    response_model=StatusResponse
)
async def get_status(status_id: int):
    try:
        status = Status.get_by_id(status_id)

        return StatusResponse.model_validate(
            status
        )

    except DoesNotExist:
        raise HTTPException(
            404,
            "Status not found"
        )


@app.get("/health")
async def health():
    return {"status": "ok"}
