from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RoomBlockCreate(BaseModel):
    room_id: int = Field(..., ge=1, description="ID аудитории")
    event_id: int = Field(..., ge=1, description="ID события")
    start_datetime: datetime = Field(..., description="Начало блокировки")
    end_datetime: datetime = Field(..., description="Конец блокировки")
    status: Optional[str] = Field(default="active", pattern="^(active|cancelled|pending)$")
    comment: Optional[str] = Field(default="", max_length=500)

class RoomBlockUpdate(BaseModel):
    start_datetime: Optional[datetime] = Field(None, description="Новое начало блокировки")
    end_datetime: Optional[datetime] = Field(None, description="Новый конец блокировки")
    status: Optional[str] = Field(None, pattern="^(active|cancelled|pending)$")
    comment: Optional[str] = Field(None, max_length=500)

class RoomBlockResponse(BaseModel):
    id: int
    room_id: int
    event_id: int
    start_datetime: datetime
    end_datetime: datetime
    status: str
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True

class RoomCreate(BaseModel):
    number: str = Field(..., max_length=10, description="Номер аудитории")
    floor: int = Field(..., ge=0, description="Этаж")
    capacity: int = Field(..., ge=1, description="Вместимость")

class RoomResponse(BaseModel):
    id: int
    number: str
    floor: int
    capacity: int

    class Config:
        from_attributes = True
      
class EventCreate(BaseModel):
    title: str = Field(..., max_length=100, description="Название события")
    type: str = Field(..., max_length=50, description="Тип события")

class EventResponse(BaseModel):
    id: int
    title: str
    type: str

    class Config:
        from_attributes = True

class RoomBlockListResponse(BaseModel):
    blocks: List[RoomBlockResponse]
    total: int
