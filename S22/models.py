from peewee import *
from datetime import date, time

db = SqliteDatabase('S22.db')


class BaseModel(Model):
    class Meta:
        database = db


class Timeslot(BaseModel):
    week_day = IntegerField(constraints=[Check('week_day BETWEEN 1 AND 7')])
    pair_number = IntegerField(constraints=[Check('pair_number BETWEEN 1 AND 7')])
    start_time = TimeField()
    end_time = TimeField(constraints=[Check('end_time > start_time')])
    
    class Meta:
        table_name = 'timeslot'


class Holiday(BaseModel):
    date = DateField(unique=True)

    class Meta:
        table_name = 'holiday'

class Short(BaseModel):
    date = DateField()
    pair_number = IntegerField(constraints=[Check('pair_number BETWEEN 1 AND 7')])
    start_time = TimeField()
    end_time = TimeField(constraints=[Check('end_time > start_time')])

    class Meta:
        table_name = 'short'


def create_tables():
    db.create_tables([Timeslot, Holiday, Short])


if __name__ == '__main__':
    create_tables()
