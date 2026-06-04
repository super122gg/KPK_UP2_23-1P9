from datetime import datetime, timezone
from peewee import *

db = SqliteDatabase('room_availability.db')

class BaseModel(Model):
    class Meta:
        database = db

class Status(BaseModel):
    ACTIVE_STATUS_ID = 1
    CANCELLED_STATUS_ID = 2
    PENDING_STATUS_ID = 3

    id = IntegerField(primary_key=True)
    name = CharField(max_length=20, unique=True)
    description = CharField(max_length=100, default='')
    is_active = BooleanField(default=True)

class RoomBlock(BaseModel):
    id = AutoField()
    room_id = IntegerField(null=False, constraints=[Check('room_id > 0')])
    event_id = IntegerField(null=False, constraints=[Check('event_id > 0')])
    status_id = ForeignKeyField(
        Status,
        backref='blocks',
        null=False,
        default=Status.ACTIVE_STATUS_ID,
        constraints=[Check('status_id > 0')]
    )
    start_datetime = DateTimeField()
    end_datetime = DateTimeField()
    comment = CharField(max_length=500, default='')
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    class Meta:
        constraints = [
            Check('end_datetime > start_datetime')
        ]

    def save(self, *args, **kwargs):
        if self.start_datetime.tzinfo is None:
            start = self.start_datetime.replace(tzinfo=timezone.utc)
        else:
            start = self.start_datetime.astimezone(timezone.utc)
        if start <= datetime.now(timezone.utc):
            raise ValueError("start_datetime cannot be in the past")
        return super().save(*args, **kwargs)

def init_db(close_after: bool = False):
    """Создаёт таблицы, если их нет."""
    try:
        db.connect(reuse_if_open=True)
        db.create_tables([Status, RoomBlock], safe=True)
        if close_after:
            db.close()
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

if __name__ == "__main__":
    init_db(close_after=True)
