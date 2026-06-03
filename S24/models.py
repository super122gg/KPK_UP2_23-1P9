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
            Check('end_datetime > start_datetime'),
            SQL('UNIQUE(room_id, start_datetime, end_datetime)')
        ]

    @classmethod
    def active(cls):
        return cls.select().where(cls.is_deleted == False)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    @staticmethod
    def validate_not_past(start_datetime: datetime) -> bool:
        now = datetime.now(timezone.utc)
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        return start_datetime > now

    @classmethod
    def has_time_overlap(
        cls,
        room_id: int,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_id: int = None
    ):
        query = cls.select().where(
            (cls.is_deleted == False) &
            (cls.room_id == room_id) &
            (cls.status_id != Status.CANCELLED_STATUS_ID) &
            (cls.start_datetime < end_datetime) &
            (cls.end_datetime > start_datetime)
        )

        if exclude_id:
            query = query.where(cls.id != exclude_id)

        return query.exists()

    @classmethod
    def has_duplicate(
        cls,
        room_id: int,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_id: int = None
    ):
        query = cls.select().where(
            (cls.is_deleted == False) &
            (cls.room_id == room_id) &
            (cls.start_datetime == start_datetime) &
            (cls.end_datetime == end_datetime)
        )

        if exclude_id:
            query = query.where(cls.id != exclude_id)

        return query.exists()

    def save(self, *args, **kwargs):
        with db.atomic():
            now = self._now()
            self.updated_at = now

            if not self.validate_not_past(self.start_datetime):
                raise ValueError("start_datetime cannot be in the past")

            if self.end_datetime <= self.start_datetime:
                raise ValueError("end_datetime must be greater than start_datetime")

            if self.has_duplicate(
                self.room_id,
                self.start_datetime,
                self.end_datetime,
                self.id
            ):
                raise ValueError("Duplicate block")

            if (
                not self.is_deleted and
                self.status_id != Status.CANCELLED_STATUS_ID and
                self.has_time_overlap(
                    self.room_id,
                    self.start_datetime,
                    self.end_datetime,
                    self.id
                )
            ):
                raise ValueError("Time overlap")

            return super().save(*args, **kwargs)

    @classmethod
    def soft_delete(cls, block_id: int) -> bool:
        try:
            block = cls.get_by_id(block_id)
        except cls.DoesNotExist:
            return False

        if block.is_deleted:
            return False

        block.is_deleted = True
        block.updated_at = datetime.now(timezone.utc)
        block.save()
        return True


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
