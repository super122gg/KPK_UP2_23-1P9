from datetime import datetime
from peewee import (
    SqliteDatabase, Model, AutoField, IntegerField, CharField,
    FloatField, BooleanField, DateTimeField, Check
)

db = SqliteDatabase('workload.db')


class BaseModel(Model):
    class Meta:
        database = db


class Workload(BaseModel):
    """Основная сущность: нагрузка преподавателя.
    teacher_id — внешний ID из Profile Service.
    discipline_id — внешний ID из Discipline Service."""
    id = AutoField(primary_key=True)
    teacher_id = IntegerField()
    discipline_id = IntegerField()
    hours_per_week = FloatField(constraints=[Check('hours_per_week >= 1 AND hours_per_week <= 54')])
    groups_count = IntegerField(constraints=[Check('groups_count >= 1 AND groups_count <= 10')])
    semester = IntegerField(constraints=[Check('semester = 1 OR semester = 2')])
    year = IntegerField(constraints=[Check('year >= 2020 AND year <= 2030')])
    total_hours = FloatField()
    notes = CharField(max_length=500, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        table_name = 'workloads'
        indexes = (
            (('teacher_id', 'discipline_id', 'semester', 'year'), True),
        )

    def save(self, *args, **kwargs):
        self.total_hours = self.hours_per_week * self.groups_count * 18
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    @classmethod
    def soft_delete(cls, workload_id):
        """Мягкое удаление: is_active = False. Возвращает True если деактивировано, иначе False."""
        updated = cls.update(is_active=False).where(
            (cls.id == workload_id) & (cls.is_active == True)
        ).execute()
        return updated > 0


def init_db():
    """Функция инициализации базы данных"""
    db.connect()
    db.create_tables([Workload], safe=True)

    if not Workload.select().exists():
        Workload.create(
            teacher_id=1,
            discipline_id=1,
            hours_per_week=4.0,
            groups_count=2,
            semester=1,
            year=2024,
            notes='Лекции и практика'
        )


if __name__ == '__main__':
    init_db()
    print("База данных workload.db успешно инициализирована.")