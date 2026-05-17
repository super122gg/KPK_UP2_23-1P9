from datetime import datetime
from models import RoomBlock
from peewee import fn

def check_time_overlap(room_id: int, start: datetime, end: datetime, exclude_id: int = None) -> bool:
    query = RoomBlock.select().where(
        (RoomBlock.room_id == room_id) &
        (RoomBlock.is_deleted == False) &
        (RoomBlock.status != 'cancelled') &
        (
            (RoomBlock.start_datetime < end) &
            (RoomBlock.end_datetime > start)
        )
    )
    if exclude_id:
        query = query.where(RoomBlock.id != exclude_id)
    
    return query.exists()

def validate_datetime(start: datetime, end: datetime) -> tuple:
    if start > end:
        return False, "start_datetime должен быть раньше end_datetime"
    if start < datetime.now():
        return False, "start_datetime не может быть в прошлом"
    return True, ""
