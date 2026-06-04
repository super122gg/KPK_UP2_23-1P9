"""
Модели базы данных для сервиса Room Availability.

Содержит:
- Status: справочник статусов блокировок (active, cancelled, pending)
- RoomBlock: записи о блокировках аудиторий

Поля с суффиксом _id (room_id, event_id) являются внешними идентификаторами
и ссылаются на данные в других сервисах (Room Service, сервис событий).
"""

from datetime import datetime, timezone
from peewee import *

db = SqliteDatabase('room_availability.db')


class BaseModel(Model):
    """Базовый класс модели с подключением к БД."""
    class Meta:
        database = db


class Status(BaseModel):
    """
    Справочник статусов блокировки.

    Поля:
    - id: первичный ключ (1 – active, 2 – cancelled, 3 – pending)
    - name: уникальное название статуса (1–20 символов)
    - description: описание (до 100 символов)
    - is_active: признак мягкого удаления (True – активен)
    """
    ACTIVE_STATUS_ID = 1
    CANCELLED_STATUS_ID = 2
    PENDING_STATUS_ID = 3

    id = IntegerField(primary_key=True, help_text="ID статуса (1-3)")
    name = CharField(max_length=20, unique=True, help_text="Уникальное название статуса")
    description = CharField(max_length=100, default='', help_text="Описание статуса")
    is_active = BooleanField(default=True, help_text="Активен (True) или удалён (False)")


class RoomBlock(BaseModel):
    """
    Блокировка аудитории на определённый интервал времени.

    Поля:
    - id: первичный ключ
    - room_id: ID аудитории (внешний, ссылается на Room Service)
    - event_id: ID события (внешний, ссылается на сервис событий)
    - status_id: внешний ключ на Status (определяет тип блокировки)
    - start_datetime, end_datetime: начало и конец блокировки
    - comment: комментарий (до 500 символов)
    - is_active: мягкое удаление (True – активная запись)
    - created_at, updated_at: временные метки
    """
    id = AutoField(help_text="Уникальный идентификатор блокировки")

    room_id = IntegerField(
        null=False,
        constraints=[Check('room_id > 0')],
        help_text="ID аудитории (внешний ключ на Room Service)"
    )
    event_id = IntegerField(
        null=False,
        constraints=[Check('event_id > 0')],
        help_text="ID события (внешний ключ на сервис событий)"
    )
    status_id = ForeignKeyField(
        Status,
        backref='blocks',
        null=False,
        default=1,  # 1 – active (вместо константы, чтобы удовлетворить требованию)
        constraints=[Check('status_id > 0')],
        help_text="ID статуса блокировки (ссылка на Status)"
    )
    start_datetime = DateTimeField(help_text="Дата и время начала блокировки")
    end_datetime = DateTimeField(help_text="Дата и время окончания блокировки")
    comment = CharField(max_length=500, default='', help_text="Комментарий к блокировке")
    is_active = BooleanField(default=True, help_text="Активна (True) или удалена (False)")

    created_at = DateTimeField(
        default=lambda: datetime.now(timezone.utc),
        help_text="Дата создания записи (UTC)"
    )
    updated_at = DateTimeField(
        default=lambda: datetime.now(timezone.utc),
        help_text="Дата последнего обновления (UTC)"
    )

    class Meta:
        constraints = [
            Check('end_datetime > start_datetime'),
        ]
        # Индекс для ускорения запросов (не уникальный, уникальность проверяется в бизнес-логике)
        indexes = [
            (('room_id', 'start_datetime', 'end_datetime'), False),
        ]

    def save(self, *args, **kwargs):
        """
        Сохраняет запись в БД с предварительной валидацией.

        Проверяет:
        - start_datetime не может быть в прошлом
        - end_datetime > start_datetime
        - Уникальность комбинации (room_id, start_datetime, end_datetime) для активных записей
        - Отсутствие пересечений интервалов для активных блокировок (кроме статуса cancelled)

        Выбрасывает ValueError при нарушении любого правила.
        """
        now = datetime.now(timezone.utc)

        # Приводим даты к UTC для корректного сравнения
        if self.start_datetime.tzinfo is None:
            start = self.start_datetime.replace(tzinfo=timezone.utc)
        else:
            start = self.start_datetime.astimezone(timezone.utc)

        if self.end_datetime.tzinfo is None:
            end = self.end_datetime.replace(tzinfo=timezone.utc)
        else:
            end = self.end_datetime.astimezone(timezone.utc)

        # 1. Проверка start_datetime не в прошлом
        if start <= now:
            raise ValueError("start_datetime cannot be in the past")

        # 2. Проверка end_datetime > start_datetime
        if end <= start:
            raise ValueError("end_datetime must be greater than start_datetime")

        # 3. Уникальность комбинации (room_id, start_datetime, end_datetime) для активных записей
        duplicate_query = RoomBlock.select().where(
            (RoomBlock.is_active == True) &
            (RoomBlock.id != self.id) &
            (RoomBlock.room_id == self.room_id) &
            (RoomBlock.start_datetime == self.start_datetime) &
            (RoomBlock.end_datetime == self.end_datetime)
        )
        if duplicate_query.exists():
            raise ValueError("Duplicate block (room_id, start_datetime, end_datetime)")

        # 4. Проверка пересечения интервалов для активных блокировок (кроме статуса cancelled)
        if self.is_active and self.status_id != Status.CANCELLED_STATUS_ID:
            overlap_query = RoomBlock.select().where(
                (RoomBlock.is_active == True) &
                (RoomBlock.id != self.id) &
                (RoomBlock.room_id == self.room_id) &
                (RoomBlock.status_id != Status.CANCELLED_STATUS_ID) &
                (RoomBlock.start_datetime < self.end_datetime) &
                (RoomBlock.end_datetime > self.start_datetime)
            )
            if overlap_query.exists():
                raise ValueError("Time overlap with existing active block")

        # Обновляем updated_at перед сохранением
        self.updated_at = now
        return super().save(*args, **kwargs)


def init_db(close_after: bool = False):
    """
    Создаёт таблицы базы данных, если они ещё не существуют.

    Не заполняет справочники – это делает service.py при старте приложения.
    """
    try:
        db.connect(reuse_if_open=True)
        db.create_tables([Status, RoomBlock], safe=True)
        if close_after:
            db.close()
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


if __name__ == "__main__":
    # При прямом запуске создаём только таблицы (без данных)
    init_db(close_after=True)
