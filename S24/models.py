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

    room_id = IntegerField(
        null=False,
        constraints=[Check('room_id > 0')]
    )

    event_id = IntegerField(
        null=False,
        constraints=[Check('event_id > 0')]
    )

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

    created_at = DateTimeField(
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = DateTimeField(
        default=lambda: datetime.now(timezone.utc)
    )

    class Meta:
        constraints = [
            Check('end_datetime > start_datetime')
        ]

        indexes = (
            (
                ('room_id', 'start_datetime', 'end_datetime'),
                False
            ),
        )

    @classmethod
    def active(cls):
        return cls.select().where(cls.is_deleted == False)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)

        if self.start_datetime.tzinfo is None:
            start = self.start_datetime.replace(tzinfo=timezone.utc)
        else:
            start = self.start_datetime.astimezone(timezone.utc)

        if start <= now:
            raise ValueError(
                "start_datetime cannot be in the past"
            )

        duplicate_query = RoomBlock.select().where(
            (RoomBlock.is_deleted == False) &
            (RoomBlock.id != self.id) &
            (RoomBlock.room_id == self.room_id) &
            (RoomBlock.start_datetime == self.start_datetime) &
            (RoomBlock.end_datetime == self.end_datetime)
        )

        if duplicate_query.exists():
            raise ValueError(
                "Duplicate block (room_id, start_datetime, end_datetime)"
            )

        if (
            not self.is_deleted and
            self.status_id != Status.CANCELLED_STATUS_ID
        ):
            overlap_query = RoomBlock.select().where(
                (RoomBlock.is_deleted == False) &
                (RoomBlock.id != self.id) &
                (RoomBlock.room_id == self.room_id) &
                (RoomBlock.status_id != Status.CANCELLED_STATUS_ID) &
                (RoomBlock.start_datetime < self.end_datetime) &
                (RoomBlock.end_datetime > self.start_datetime)
            )

            if overlap_query.exists():
                raise ValueError(
                    "Time overlap with existing active block"
                )

        return super().save(*args, **kwargs)


def init_db(close_after: bool = False):
    try:
        db.connect(reuse_if_open=True)

        db.create_tables(
            [Status, RoomBlock],
            safe=True
        )

        statuses = (
            (1, 'active', 'Active block'),
            (2, 'cancelled', 'Cancelled block'),
            (3, 'pending', 'Pending confirmation'),
        )

        for status_id, name, description in statuses:
            Status.get_or_create(
                id=status_id,
                defaults={
                    'name': name,
                    'description': description
                }
            )

        if close_after:
            db.close()

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


if __name__ == "__main__":
    init_db(close_after=True)
