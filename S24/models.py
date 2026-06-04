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
        default=1,
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
        # Неуникальный индекс для ускорения запросов (уникальность проверяется в service.py)
        indexes = [
            (('room_id', 'start_datetime', 'end_datetime'), False),
        ]

    # Метод save() удалён – вся бизнес-логика (проверка дат, уникальности, пересечений)
    # вынесена в service.py, что соответствует требованиям.

def init_db(close_after: bool = False):
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
