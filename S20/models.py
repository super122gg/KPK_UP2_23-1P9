from datetime import datetime, date
from peewee import (
    SqliteDatabase, Model, AutoField, CharField, IntegerField,
    ForeignKeyField, DateTimeField, DateField, BooleanField, Check
)

db = SqliteDatabase('academic_period.db')


class BaseModel(Model):
    class Meta:
        database = db


class AcademicYear(BaseModel):
    """Учебный год, к которому привязаны периоды"""
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True, constraints=[Check("length(name) >= 1")])
    start_date = DateField()
    end_date = DateField()
    is_active = BooleanField(default=True)

    class Meta:
        table_name = 'academic_years'


class PeriodType(BaseModel):
    """Справочник типов периодов: Семестр, Модуль, Четверть и т.д."""
    id = AutoField(primary_key=True)
    name = CharField(max_length=50, unique=True, constraints=[Check("length(name) >= 1")])
    description = CharField(max_length=200, null=True)

    class Meta:
        table_name = 'period_types'


class AcademicPeriod(BaseModel):
    """Основная сущность: учебный период (семестр, модуль и т.д.)"""
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, constraints=[Check("length(name) >= 1")])
    academic_year = ForeignKeyField(AcademicYear, backref='periods', on_delete='RESTRICT')
    period_type = ForeignKeyField(PeriodType, backref='periods', on_delete='RESTRICT')
    start_date = DateField()
    end_date = DateField()
    order_num = IntegerField(constraints=[Check('order_num >= 1')])
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'academic_periods'
        indexes = (
            (('academic_year', 'period_type', 'order_num'), True),
        )

    def save(self, *args, **kwargs):
        if self.end_date < self.start_date:
            raise ValueError("end_date должна быть позже start_date")
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    @classmethod
    def soft_delete(cls, period_id):
        """Мягкое удаление: is_active = False. Возвращает True если деактивировано, иначе False."""
        updated = cls.update(is_active=False).where(
            (cls.id == period_id) & (cls.is_active == True)
        ).execute()
        return bool(updated)


class PeriodGroup(BaseModel):
    """Транзитивная таблица: связь многие ко многим между AcademicPeriod и Group.
    group_id — внешний ID из Group Service, не хранится локально."""
    id = AutoField(primary_key=True)
    period = ForeignKeyField(AcademicPeriod, backref='period_groups', on_delete='CASCADE')
    group_id = IntegerField()

    class Meta:
        table_name = 'period_groups'
        indexes = (
            (('period', 'group_id'), True),
        )


def init_db():
    """Создание таблиц и заполнение начальными данными"""
    db.connect()
    db.create_tables([AcademicYear, PeriodType, AcademicPeriod, PeriodGroup], safe=True)

    if not AcademicYear.select().exists():
        year = AcademicYear.create(
            name='2024-2025',
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30)
        )

        sem = PeriodType.create(name='Семестр', description='Полугодовой период обучения')
        PeriodType.create(name='Модуль', description='Четвертной модуль обучения')

        p1 = AcademicPeriod.create(
            name='1 семестр 2024-2025',
            academic_year=year,
            period_type=sem,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 1, 25),
            order_num=1
        )
        AcademicPeriod.create(
            name='2 семестр 2024-2025',
            academic_year=year,
            period_type=sem,
            start_date=date(2025, 2, 3),
            end_date=date(2025, 6, 28),
            order_num=2
        )

        PeriodGroup.create(period=p1, group_id=1)
        PeriodGroup.create(period=p1, group_id=2)


if __name__ == '__main__':
    init_db()
    print("База данных academic_period.db успешно инициализирована.")