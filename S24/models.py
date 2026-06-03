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
    name = CharField(unique=True, max_length=20)
    description = CharField(max_length=100)


class RoomBlock(BaseModel):
    id = AutoField()
    room_id = IntegerField(null=False, constraints=[Check('room_id > 0')])
    event_id = IntegerField(null=False, constraints=[Check('event_id > 0')])

    status_id = ForeignKeyField(
        Status,
        backref='blocks',
        null=False,
        default=Status.ACTIVE_STATUS_ID
    )

    start_datetime = DateTimeField()
    end_datetime = DateTimeField()

    comment = CharField(max_length=500, default='')
    is_deleted = BooleanField(default=False)

    created_at = DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = DateTimeField(default=lambda: datetime.now(timezone.utc))

    class Meta:
        constraints = [
            Check('end_datetime > start_datetime')
        ]

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    @classmethod
    def active(cls):
        return cls.select().where(cls.is_deleted == False)

    @classmethod
    def is_unique_active(cls, room_id: int, start: datetime, end: datetime, exclude_id: int = None) -> bool:
        query = cls.select().where(
            (cls.is_deleted == False) &
            (cls.room_id == room_id) &
            (cls.start_datetime == start) &
            (cls.end_datetime == end)
        )
        if exclude_id:
            query = query.where(cls.id != exclude_id)
        return not query.exists()


def init_db(close_after: bool = False):
    try:
        db.connect(reuse_if_open=True)
        db.create_tables([Status, RoomBlock], safe=True)

        statuses = (
            (1, 'active', 'Active block'),
            (2, 'cancelled', 'Cancelled block'),
            (3, 'pending', 'Pending confirmation'),
        )

        for status_id, name, description in statuses:
            Status.get_or_create(
                id=status_id,
                defaults={'name': name, 'description': description}
            )

        if close_after:
            db.close()
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


if __name__ == "__main__":
    init_db(close_after=True)
