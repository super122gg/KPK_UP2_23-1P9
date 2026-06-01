from peewee import (
    Model, CharField, BooleanField, ForeignKeyField,
    TimeField, IntegerField, SqliteDatabase, CompositeKey
)

db = SqliteDatabase('teacher_availability.db')


class BaseModel(Model):
    class Meta:
        database = db


class Teacher(BaseModel):
    full_name = CharField(max_length=100)
    can_teach_remote = BooleanField(default=False)
    is_active = BooleanField(default=True)


class TimeSlot(BaseModel):
    day_of_week = IntegerField()  # 1=Пн..7=Вс
    start_time = TimeField()
    end_time = TimeField()
    is_active = BooleanField(default=True)

    class Meta:
        indexes = (
            (('day_of_week', 'start_time', 'end_time'), True),  # уникальность
        )


class TeacherTimePreference(BaseModel):
    teacher = ForeignKeyField(Teacher, backref='time_preferences')
    time_slot = ForeignKeyField(TimeSlot, backref='teacher_preferences')
    preference_type = CharField(max_length=32)  # 'methodical_day' / 'unavailable'
    is_active = BooleanField(default=True)

    class Meta:
        primary_key = CompositeKey('teacher', 'time_slot')


def init_db():
    db.connect()
    db.create_tables([Teacher, TimeSlot, TeacherTimePreference], safe=True)
    db.close()


if __name__ == '__main__':
    init_db()
    print("База данных инициализирована.")