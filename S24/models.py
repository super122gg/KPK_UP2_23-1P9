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


class RoomBlock(BaseModel):
    room_id = IntegerField(
        null=False,
        constraints=[Check('room_id > 0')]
    )

    event_id = IntegerField(
        null=False,
        constraints=[Check('event_id > 0')]
    )

    status_id = IntegerField(
        null=False,
        default=Status.ACTIVE_STATUS_ID,
        constraints=[Check('status_id > 0')]
    )

    start_datetime = DateTimeField()
    end_datetime = DateTimeField()

    comment = CharField(
        max_length=500,
        default=''
    )

    is_deleted = BooleanField(default=False)

    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    @classmethod
    def active(cls):
        return cls.select().where(
            cls.is_deleted == False
        )

    @staticmethod
    def validate_not_past(start_datetime: datetime) -> bool:
        now = datetime.now()
        return start_datetime >= now

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

        if exclude_id is not None:
            query = query.where(
                cls.id != exclude_id
            )

        return query.exists()

    def save(self, *args, **kwargs):
        now = datetime.now()

        if not self.validate_not_past(
            self.start_datetime
        ):
            raise ValueError(
                'start_datetime не может быть в прошлом'
            )

        if self.end_datetime <= self.start_datetime:
            raise ValueError(
                'end_datetime должен быть позже start_datetime'
            )

        exclude_id = self.id

        if (
            not self.is_deleted and
            self.status_id != Status.CANCELLED_STATUS_ID and
            self.has_time_overlap(
                self.room_id,
                self.start_datetime,
                self.end_datetime,
                exclude_id
            )
        ):
            raise ValueError(
                'В это время аудитория уже занята'
            )

        self.updated_at = now

        return super().save(*args, **kwargs)

    @classmethod
    def soft_delete(cls, block_id: int):
        try:
            block = cls.get_by_id(block_id)
        except cls.DoesNotExist:
            return False

        if block.is_deleted:
            return False

        block.is_deleted = True
        block.save()

        return True

    class Meta:
        constraints = [
            SQL(
                'UNIQUE(room_id, start_datetime, end_datetime)'
            ),
            Check(
                "length(comment) <= 500"
            )
        ]


def init_db(close_after=False):
    db.connect(reuse_if_open=True)

    db.create_tables(
        [Status, RoomBlock],
        safe=True
    )

    statuses = (
        (
            Status.ACTIVE_STATUS_ID,
            'active',
            'Активная блокировка'
        ),
        (
            Status.CANCELLED_STATUS_ID,
            'cancelled',
            'Отменённая блокировка'
        ),
        (
            Status.PENDING_STATUS_ID,
            'pending',
            'Ожидает подтверждения'
        ),
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


if __name__ == '__main__':
    init_db(close_after=True)
