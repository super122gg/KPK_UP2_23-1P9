from peewee import *

db = SqliteDatabase('S22.db')


class BaseModel(Model):
    class Meta:
        database = db


class Weekday(BaseModel):
    order_number = IntegerField(
        unique=True, 
        constraints=[Check('order_number BETWEEN 1 AND 7')]
    )

    class Meta:
        table_name = 'weekday'

    @property
    def weekday_name(self) -> str:
        weekdays = {
            1: 'Понедельник',
            2: 'Вторник',
            3: 'Среда',
            4: 'Четверг',
            5: 'Пятница',
            6: 'Суббота',
            7: 'Воскресенье'
        }
        return weekdays.get(self.order_number, 'Неизвестный день')


class Timeslot(BaseModel):
    pair_number = IntegerField(
        constraints=[Check('pair_number BETWEEN 1 AND 7')],
    )
    start_time = TimeField()
    end_time = TimeField()
    duration_min = IntegerField()

    class Meta:
        table_name = 'timeslot'


class WeekdayTimeslot(BaseModel):
    weekday = ForeignKeyField(
        Weekday, 
        backref='weekday_timeslots', 
        on_delete='CASCADE',
        on_update="CASCADE"
    )
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
    db.create_tables([Weekday, Timeslot, WeekdayTimeslot])


if __name__ == '__main__':
    create_tables()
