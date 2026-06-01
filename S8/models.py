from datetime import datetime
from peewee import (
    SqliteDatabase, Model, AutoField, CharField, IntegerField,
    ForeignKeyField, DateTimeField, BooleanField, Check
)

db = SqliteDatabase('subgroup.db')


class BaseModel(Model):
    class Meta:
        database = db


class Subgroup(BaseModel):
    """Основная сущность: подгруппа внутри учебной группы.
    group_id — внешний ID из Group Service, не хранится локально."""
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, constraints=[Check("length(name) >= 1")])
    group_id = IntegerField()
    division_type = CharField(max_length=100, constraints=[Check("length(division_type) >= 1")])
    purpose = CharField(max_length=200, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'subgroups'
        indexes = (
            (('name', 'group_id'), True),  # уникальная комбинация name + group_id
        )

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    @classmethod
    def soft_delete(cls, subgroup_id):
        """Мягкое удаление: is_active = False. Возвращает True если деактивировано, иначе False."""
        updated = cls.update(is_active=False).where(
            (cls.id == subgroup_id) & (cls.is_active == True)
        ).execute()
        return updated > 0


class SubgroupStudent(BaseModel):
    """Транзитивная таблица: связь многие ко многим между Subgroup и Student.
    student_id — внешний ID из Profile Service, не хранится локально.
    division_type дублируется из Subgroup для реализации уникального индекса
    (student_id, division_type) на уровне БД."""
    id = AutoField(primary_key=True)
    subgroup = ForeignKeyField(Subgroup, backref='subgroup_students', on_delete='CASCADE')
    student_id = IntegerField()
    division_type = CharField(max_length=100)
    joined_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'subgroup_students'
        indexes = (
            (('subgroup', 'student_id'), True),       # студент в одной подгруппе только один раз
            (('student_id', 'division_type'), True),  # студент только в одной подгруппе по типу деления
        )


def init_db():
    """Создание таблиц и заполнение начальными данными"""
    db.connect()
    db.create_tables([Subgroup, SubgroupStudent], safe=True)

    if not Subgroup.select().exists():
        sg1 = Subgroup.create(
            name='Подгруппа 1',
            group_id=1,
            division_type='Иностранный язык',
            purpose='Английский язык — группа A'
        )
        sg2 = Subgroup.create(
            name='Подгруппа 2',
            group_id=1,
            division_type='Иностранный язык',
            purpose='Английский язык — группа B'
        )

        SubgroupStudent.create(subgroup=sg1, student_id=1, division_type='Иностранный язык')
        SubgroupStudent.create(subgroup=sg1, student_id=2, division_type='Иностранный язык')
        SubgroupStudent.create(subgroup=sg2, student_id=3, division_type='Иностранный язык')


if __name__ == '__main__':
    init_db()
    print("База данных subgroup.db успешно инициализирована.")