from datetime import datetime
from models import CANCELLED_STATUS_ID, RoomBlock



def check_time_overlap(
    room_id: int,
    start: datetime,
    end: datetime,
    exclude_id: int = None,
) -> bool:
    query = RoomBlock.select().where(
        (RoomBlock.room_id == room_id) &
        (RoomBlock.is_deleted == False) &
        (RoomBlock.status_id != CANCELLED_STATUS_ID) &
        (RoomBlock.start_datetime < end) &
        (RoomBlock.end_datetime > start)
    )
    if exclude_id is not None:
        query = query.where(RoomBlock.id != exclude_id)
    return query.exists()


def validate_datetime(start: datetime, end: datetime, check_past: bool = True) -> tuple:
    if start >= end:
        return False, 'end_datetime должен быть позже start_datetime'
    if check_past and start < datetime.now():
        return False, 'start_datetime не может быть в прошлом'
    return True, ''
