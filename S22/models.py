from peewee import *

db = SqliteDatabase('S22.db')


class BaseModel(Model):
    class Meta:
        database = db


class Timeslot(BaseModel):
    pair_number = IntegerField(
        constraints=[Check('pair_number BETWEEN 1 AND 7')],
    )
    start_time = TimeField()
    end_time = TimeField(constraints=[Check('end_time > start_time')])
    duration_min = IntegerField(constraints=[Check('duration_min > 0')])

    class Meta:
        table_name = 'timeslot'


class WeekdayTimeslot(BaseModel):
    timeslot = ForeignKeyField(
        Timeslot, 
        backref='weekday_timeslots', 
        on_delete='CASCADE',
        on_update="CASCADE"
    )
    is_shortened = BooleanField(
        default=False
    )
    is_holiday = BooleanField(
        default=False
    )

    class Meta:
        table_name = 'weekday_timeslot'


def create_tables():
    db.create_tables([Timeslot, WeekdayTimeslot])


if __name__ == '__main__':
    create_tables()
