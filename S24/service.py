from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from peewee import DoesNotExist, IntegrityError
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from models import RoomBlock, Status, db, init_db


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ensure_default_statuses():
    """Создаёт предопределённые статусы, если они отсутствуют (дубль на случай, если models.init_db не был вызван)."""
    default_statuses = [
        (1, 'active', 'Active block'),
        (2, 'cancelled', 'Cancelled block'),
        (3, 'pending', 'Pending confirmation'),
    ]
    for sid, name, desc in default_statuses:
        Status.get_or_create(
            id=sid,
            defaults={'name': name, 'description': desc, 'is_active': True}
        )


# ---------- Pydantic схемы ----------
class RoomBlockCreate(BaseModel):
    room_id: int = Field(..., ge=1)
    event_id: int = Field(..., ge=1)
    start_datetime: datetime
    end_datetime: datetime
    status_id: int = Field(default=1, ge=1)
    comment: str = Field(default="", max_length=500)

    @field_validator("start_datetime")
    @classmethod
    def validate_start_not_past(cls, v):
        v = to_utc(v)
        if v <= datetime.now(timezone.utc):
            raise ValueError("start_datetime cannot be in the past")
        return v

    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v, info: ValidationInfo):
        v = to_utc(v)
        start = info.data.get("start_datetime")
        if start is None:
            return v
        start_utc = to_utc(start)
        if v <= start_utc:
            raise ValueError("end_datetime must be greater than start_datetime")
        return v


class RoomBlockUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status_id: Optional[int] = Field(None, ge=1)
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator("start_datetime")
    @classmethod
    def validate_start_not_past(cls, v):
        if v is not None:
            v = to_utc(v)
            if v <= datetime.now(timezone.utc):
                raise ValueError("start_datetime cannot be in the past")
        return v

    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v, info: ValidationInfo):
        if v is not None:
            v = to_utc(v)
            start = info.data.get("start_datetime")
            if start is not None:
                start_utc = to_utc(start)
                if v <= start_utc:
                    raise ValueError("end_datetime must be greater than start_datetime")
        return v


class RoomBlockResponse(BaseModel):
    id: int
    room_id: int
    event_id: int
    start_datetime: datetime
    end_datetime: datetime
    status_id: int
    comment: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StatusCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    description: str = Field(default="", max_length=100)


class StatusUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=100)


class StatusResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool

    class Config:
        from_attributes = True


class DeleteResponse(BaseModel):
    success: bool


class HealthResponse(BaseModel):
    status: str


# ---------- FastAPI приложение ----------
app = FastAPI(title="Room Availability Service", version="1.0.0")


@app.on_event("startup")
def startup():
    """Инициализация БД и предопределённых статусов."""
    init_db()                 # создаёт таблицы и статусы
    ensure_default_statuses() # дополнительная гарантия


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
        is_active=block.is_active,
        created_at=block.created_at,
        updated_at=block.updated_at,
    )


def check_duplicate(room_id, start, end, exclude_id=None):
    """Проверка точного совпадения (room_id, start, end) для активных записей."""
    query = RoomBlock.select().where(
        (RoomBlock.is_active == True)
        & (RoomBlock.room_id == room_id)
        & (RoomBlock.start_datetime == start)
        & (RoomBlock.end_datetime == end)
    )
    if exclude_id:
        query = query.where(RoomBlock.id != exclude_id)
    return query.exists()


def check_overlap(room_id, start, end, exclude_id=None):
    """Проверка пересечения интервалов (кроме cancelled)."""
    query = RoomBlock.select().where(
        (RoomBlock.is_active == True)
        & (RoomBlock.room_id == room_id)
        & (RoomBlock.status_id != Status.CANCELLED_STATUS_ID)
        & (RoomBlock.start_datetime < end)
        & (RoomBlock.end_datetime > start)
    )
    if exclude_id:
        query = query.where(RoomBlock.id != exclude_id)
    return query.exists()


# ---------- Эндпоинты RoomBlock ----------
@app.post("/blocks/", response_model=RoomBlockResponse, status_code=201)
async def create_block(block: RoomBlockCreate):
    """
    Создать новую блокировку аудитории.

    - **room_id**: ID аудитории (>0)
    - **event_id**: ID события (>0)
    - **start_datetime**: начало блокировки (не в прошлом)
    - **end_datetime**: конец блокировки (> start_datetime)
    - **status_id**: ID статуса (по умолчанию 1)
    - **comment**: комментарий (<=500 символов)

    Возвращает созданный объект.
    """
    try:
        status = Status.get_by_id(block.status_id)
        if not status.is_active:
            raise HTTPException(404, "Status not found or inactive")
    except DoesNotExist:
        raise HTTPException(404, "Status not found")

    start_utc = to_utc(block.start_datetime)
    end_utc = to_utc(block.end_datetime)

    with db.atomic():
        # Уникальность (точное совпадение)
        if check_duplicate(block.room_id, start_utc, end_utc):
            raise HTTPException(409, "Duplicate block (room_id, start_datetime, end_datetime)")
        # Пересечение интервалов
        if check_overlap(block.room_id, start_utc, end_utc):
            raise HTTPException(409, "Time overlap with existing active block")

        try:
            new_block = RoomBlock.create(
                room_id=block.room_id,
                event_id=block.event_id,
                status_id=block.status_id,
                start_datetime=block.start_datetime,
                end_datetime=block.end_datetime,
                comment=block.comment,
            )
            return to_response(new_block)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except IntegrityError as e:
            # Уникальность на уровне БД (на случай гонки)
            raise HTTPException(409, "Database conflict: duplicate or overlap")


@app.patch("/blocks/{block_id}", response_model=RoomBlockResponse)
async def update_block(block_id: int, block_data: RoomBlockUpdate):
    """
    Обновить существующую блокировку (только активную).

    Параметры пути:
    - **block_id**: ID блокировки

    Тело запроса (все поля необязательны):
    - **start_datetime**
    - **end_datetime**
    - **status_id**
    - **comment**

    Возвращает обновлённый объект.
    """
    try:
        block = RoomBlock.get_by_id(block_id)
        if not block.is_active:
            raise HTTPException(404, "Block not found")

        data = block_data.model_dump(exclude_unset=True)
        if not data:
            return to_response(block)

        new_start = data.get("start_datetime", block.start_datetime)
        new_end = data.get("end_datetime", block.end_datetime)
        new_status = data.get("status_id", block.status_id)

        if "status_id" in data:
            try:
                status = Status.get_by_id(new_status)
                if not status.is_active:
                    raise HTTPException(404, "Status not found or inactive")
            except DoesNotExist:
                raise HTTPException(404, "Status not found")

        if "start_datetime" in data or "end_datetime" in data or "status_id" in data:
            new_start_utc = to_utc(new_start)
            new_end_utc = to_utc(new_end)
            if check_duplicate(block.room_id, new_start_utc, new_end_utc, block_id):
                raise HTTPException(409, "Duplicate block (room_id, start_datetime, end_datetime)")
            if check_overlap(block.room_id, new_start_utc, new_end_utc, block_id):
                raise HTTPException(409, "Time overlap with existing active block")

        for k, v in data.items():
            setattr(block, k, v)
        try:
            block.save()  # updated_at обновится автоматически в модели
        except ValueError as e:
            raise HTTPException(400, str(e))
        return to_response(block)

    except DoesNotExist:
        raise HTTPException(404, "Block not found")
    except IntegrityError as e:
        raise HTTPException(409, "Database conflict")


@app.delete("/blocks/{block_id}", response_model=DeleteResponse)
async def delete_block(block_id: int):
    """
    Мягкое удаление блокировки (устанавливает is_active=False).

    Возвращает `{"success": true}` если запись была активна и удалена,
    иначе `{"success": false}` (запись не найдена или уже удалена).
    """
    try:
        block = RoomBlock.get_by_id(block_id)
        if not block.is_active:
            return DeleteResponse(success=False)
        block.is_active = False
        block.save()
        return DeleteResponse(success=True)
    except DoesNotExist:
        return DeleteResponse(success=False)


@app.get("/blocks/{block_id}", response_model=RoomBlockResponse)
async def get_block(block_id: int):
    """Получить блокировку по ID (включая удалённые). Возвращает 404, если не найдена."""
    try:
        block = RoomBlock.get_by_id(block_id)
        return to_response(block)
    except DoesNotExist:
        raise HTTPException(404, "Block not found")


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
    """
    Получить список блокировок с фильтрацией (включая удалённые).

    Параметры фильтрации:
    - **room_id**
    - **event_id**
    - **status_id**
    - **date_from**: начало периода (end_datetime > date_from)
    - **date_to**: конец периода (start_datetime < date_to)
    - **limit**, **offset**
    """
    now = datetime.now(timezone.utc)
    if date_from and to_utc(date_from) < now:
        raise HTTPException(400, "date_from cannot be in the past")
    if date_to and to_utc(date_to) < now:
        raise HTTPException(400, "date_to cannot be in the past")

    date_from_utc = to_utc(date_from) if date_from is not None else None
    date_to_utc = to_utc(date_to) if date_to is not None else None

    if date_from_utc is not None and date_to_utc is not None and date_from_utc >= date_to_utc:
        raise HTTPException(400, "date_from must be less than date_to")

    query = RoomBlock.select()
    if room_id:
        query = query.where(RoomBlock.room_id == room_id)
    if event_id:
        query = query.where(RoomBlock.event_id == event_id)
    if status_id:
        query = query.where(RoomBlock.status_id == status_id)

    if date_from_utc and date_to_utc:
        query = query.where(
            (RoomBlock.start_datetime < date_to_utc) & (RoomBlock.end_datetime > date_from_utc)
        )
    elif date_from_utc:
        query = query.where(RoomBlock.end_datetime > date_from_utc)
    elif date_to_utc:
        query = query.where(RoomBlock.start_datetime < date_to_utc)

    query = query.order_by(RoomBlock.id).limit(limit).offset(offset)
    return [to_response(item) for item in query]


# ---------- Эндпоинты Status ----------
@app.post("/statuses/", response_model=StatusResponse, status_code=201)
async def create_status(status: StatusCreate):
    """
    Создать новый статус.

    - **name**: уникальное имя (1–20 символов)
    - **description**: описание (до 100 символов)

    Возвращает созданный объект.
    """
    try:
        new_status = Status.create(name=status.name, description=status.description)
        return StatusResponse.model_validate(new_status)
    except IntegrityError:
        raise HTTPException(409, "Status with this name already exists")


@app.patch("/statuses/{status_id}", response_model=StatusResponse)
async def update_status(status_id: int, status_data: StatusUpdate):
    """
    Обновить статус по ID.

    Параметры пути:
    - **status_id**

    Тело запроса (необязательные поля):
    - **name**
    - **description**
    """
    try:
        status = Status.get_by_id(status_id)
        data = status_data.model_dump(exclude_unset=True)
        if not data:
            return StatusResponse.model_validate(status)

        if "name" in data:
            existing = Status.select().where(Status.name == data["name"], Status.id != status_id)
            if existing.exists():
                raise HTTPException(409, "Status with this name already exists")

        for k, v in data.items():
            setattr(status, k, v)
        status.save()
        return StatusResponse.model_validate(status)
    except DoesNotExist:
        raise HTTPException(404, "Status not found")


@app.delete("/statuses/{status_id}", response_model=DeleteResponse)
async def delete_status(status_id: int):
    """
    Мягкое удаление статуса (устанавливает is_active=False).

    Возвращает `{"success": true}` если статус был активен и удалён,
    иначе `{"success": false}`.
    Если статус используется в активных блокировках, возвращает 409 Conflict.
    """
    try:
        status = Status.get_by_id(status_id)
        if not status.is_active:
            return DeleteResponse(success=False)

        used = RoomBlock.select().where(RoomBlock.status_id == status_id, RoomBlock.is_active == True).exists()
        if used:
            raise HTTPException(409, "Status is used in active room blocks and cannot be deleted")

        status.is_active = False
        status.save()
        return DeleteResponse(success=True)
    except DoesNotExist:
        return DeleteResponse(success=False)


@app.get("/statuses/{status_id}", response_model=StatusResponse)
async def get_status(status_id: int):
    """Получить статус по ID (включая удалённые)."""
    try:
        status = Status.get_by_id(status_id)
        return StatusResponse.model_validate(status)
    except DoesNotExist:
        raise HTTPException(404, "Status not found")


@app.get("/statuses/", response_model=List[StatusResponse])
async def get_statuses():
    """Получить список всех статусов (включая удалённые)."""
    return [StatusResponse.model_validate(s) for s in Status.select()]


@app.get("/health", response_model=HealthResponse)
async def health():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}
