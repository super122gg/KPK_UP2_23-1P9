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
        # Индекс удалён – уникальность для активных записей проверяется в бизнес-логике (service.py)
        # SQLite не поддерживает частичные уникальные индексы с условием WHERE is_active = true

    def save(self, *args, **kwargs):
        # Автоматическое обновление поля updated_at при каждом сохранении
        self.updated_at = datetime.now(timezone.utc)
        # Вся бизнес-логика (проверка пересечений, дубликатов) вынесена в service.py
        return super().save(*args, **kwargs)

def init_db(close_after: bool = False):
    try:
        db.connect(reuse_if_open=True)
        db.create_tables([Status, RoomBlock], safe=True)

        # Предопределённые статусы – вставляем только если их нет (без обновления существующих)
        statuses = [
            (1, 'active', 'Active block'),
            (2, 'cancelled', 'Cancelled block'),
            (3, 'pending', 'Pending confirmation'),
        ]
        for status_id, name, description in statuses:
            Status.get_or_create(
                id=status_id,
                defaults={'name': name, 'description': description, 'is_active': True}
            )

        if close_after:
            db.close()
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

if __name__ == "__main__":
    init_db(close_after=True)
