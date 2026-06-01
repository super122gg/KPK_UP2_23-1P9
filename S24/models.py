from datetime import datetime

from peewee import *

db = SqliteDatabase('room_availability.db')

ACTIVE_STATUS_ID = 1
CANCELLED_STATUS_ID = 2


class BaseModel(Model):
    class Meta:
        database = db


class Status(BaseModel):
    name = CharField(unique=True, max_length=20)
    description = CharField(max_length=100, null=True)


class Room(BaseModel):
    number = CharField(unique=True, max_length=10)
    floor = IntegerField(constraints=[Check('floor >= 0')])
    capacity = IntegerField(constraints=[Check('capacity > 0')])


class Event(BaseModel):
    title = CharField(max_length=100)
    event_type = CharField(column_name='type', max_length=50)

    @property
    def type(self):
        return self.event_type


class RoomBlock(BaseModel):
    room_id = ForeignKeyField(Room, backref='blocks', null=False, on_delete='CASCADE', column_name='room_id')
    event_id = ForeignKeyField(Event, backref='blocks', null=False, on_delete='CASCADE', column_name='event_id')
    status_id = ForeignKeyField(
        Status,
        backref='blocks',
        null=False,
        on_delete='RESTRICT',
        column_name='status_id',
        default=ACTIVE_STATUS_ID,
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

    class Meta:
        indexes = [
            (('room_id', 'start_datetime', 'end_datetime'), True),
        ]
        constraints = [
            Check('end_datetime > start_datetime'),
        ]


def init_db(close_after: bool = False):
    db.connect(reuse_if_open=True)
    db.create_tables([Status, Room, Event, RoomBlock], safe=True)
    for name in ('active', 'cancelled', 'pending'):
        if not Status.select().where(Status.name == name).exists():
            Status.create(name=name)
    if close_after:
        db.close()


if __name__ == '__main__':
    init_db(close_after=True)
