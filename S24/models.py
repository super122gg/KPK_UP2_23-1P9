from datetime import datetime

from peewee import *

db = SqliteDatabase('room_availability.db')


class BaseModel(Model):
    class Meta:
        database = db


class Status(BaseModel):
    ACTIVE_STATUS_ID = 1
    CANCELLED_STATUS_ID = 2
    PENDING_STATUS_ID = 3
    name = CharField(unique=True, max_length=20)
    description = CharField(max_length=100)


ACTIVE_STATUS_ID = Status.ACTIVE_STATUS_ID
CANCELLED_STATUS_ID = Status.CANCELLED_STATUS_ID


class Room(BaseModel):
    number = CharField(unique=True, max_length=10)
    floor = IntegerField(constraints=[Check('floor >= 0')])
    capacity = IntegerField(constraints=[Check('capacity > 0')])


class Event(BaseModel):
    title = CharField(max_length=100)
    type = CharField(max_length=50)


class RoomBlock(BaseModel):
    room_id = ForeignKeyField(Room, backref='blocks', null=False, on_delete='CASCADE', column_name='room_id')
    event_id = ForeignKeyField(Event, backref='blocks', null=False, on_delete='CASCADE', column_name='event_id')
    status_id = ForeignKeyField(
        Status,
        backref='blocks',
        null=False,
        on_delete='RESTRICT',
        column_name='status_id',
        default=Status.ACTIVE_STATUS_ID,
    )
    start_datetime = DateTimeField()
    end_datetime = DateTimeField()
    comment = CharField(max_length=500, default='')
    is_deleted = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    def save(self, *args, **kwargs):
        if self.id is not None:
            self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    @classmethod
    def active(cls):
        return cls.select().where(cls.is_deleted == False)

    @staticmethod
    def validate_not_past(start_datetime: datetime, check_past: bool = True) -> bool:
        if not check_past:
            return True
        return start_datetime >= datetime.now()

    @classmethod
    def has_time_overlap(cls, room_id: int, start_datetime: datetime, end_datetime: datetime, exclude_id: int = None) -> bool:
        query = cls.active().where(
            (cls.room_id == room_id) &
            (cls.status_id != Status.CANCELLED_STATUS_ID) &
            (cls.start_datetime < end_datetime) &
            (cls.end_datetime > start_datetime)
        )
        if exclude_id is not None:
            query = query.where(cls.id != exclude_id)
        return query.exists()

    class Meta:
        constraints = [
            SQL('UNIQUE(room_id, start_datetime, end_datetime)'),
            Check('end_datetime > start_datetime'),
        ]


def init_db(close_after: bool = False):
    db.connect(reuse_if_open=True)
    db.create_tables([Status, Room, Event, RoomBlock], safe=True)
    statuses = (
        (Status.ACTIVE_STATUS_ID, 'active', 'Активная блокировка'),
        (Status.CANCELLED_STATUS_ID, 'cancelled', 'Отменённая блокировка'),
        (Status.PENDING_STATUS_ID, 'pending', 'Ожидает подтверждения'),
    )
    for status_id, name, description in statuses:
        status, created = Status.get_or_create(
            id=status_id,
            defaults={'name': name, 'description': description},
        )
        if not created:
            status.name = name
            status.description = description
            status.save()
    if close_after:
        db.close()


if __name__ == '__main__':
    init_db(close_after=True)
