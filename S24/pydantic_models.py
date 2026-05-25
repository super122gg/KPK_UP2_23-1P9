from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class StatusCreate(BaseModel):
    name: str = Field(..., max_length=20)
    description: Optional[str] = Field(None, max_length=100)

class StatusResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True

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

    @field_validator('start_datetime')
    def check_not_past(cls, v):
        if v < datetime.now():
            raise ValueError('start_datetime не может быть в прошлом')
        return v

    @field_validator('end_datetime')
    def check_end_after_start(cls, v, info):
        if 'start_datetime' in info.data and v <= info.data['start_datetime']:
            raise ValueError('end_datetime должен быть позже start_datetime')
        return v

class RoomBlockUpdate(BaseModel):
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status_id: Optional[int] = Field(None, ge=1)
    comment: Optional[str] = Field(None, max_length=500)

class RoomBlockResponse(BaseModel):
    id: int
    room_id: int
    event_id: int
    start_datetime: datetime
    end_datetime: datetime
    status_id: int
    comment: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
