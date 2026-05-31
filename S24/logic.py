from datetime import datetime
from models import RoomBlock, Status
from peewee import fn

def check_time_overlap(room_id: int, start: datetime, end: datetime, exclude_id: int = None) -> bool:
    try:
        cancelled_status = Status.get(Status.name == 'cancelled')
    except Status.DoesNotExist:
        cancelled_status = None
    query = RoomBlock.select().join(Status).where(
        (RoomBlock.room_id == room_id) &
        (RoomBlock.is_deleted == False)
    )
    if cancelled_status:
        query = query.where(RoomBlock.status_id != cancelled_status.id)
    query = query.where(
        (RoomBlock.start_datetime < end) &
        (RoomBlock.end_datetime > start)
    )
    if exclude_id:
        query = query.where(RoomBlock.id != exclude_id)
    return query.exists()

def validate_datetime(start: datetime, end: datetime, check_past: bool = True) -> tuple:
    if start >= end:
        return False, "end_datetime должен быть позже start_datetime"
    if check_past and start < datetime.now():
        return False, "start_datetime не может быть в прошлом"
    return True, ""
