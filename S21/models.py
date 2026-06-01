from peewee import (
    Model, CharField, TextField, BooleanField, ForeignKeyField,
    DateField, SqliteDatabase, CompositeKey
)

db = SqliteDatabase('holidays.db')

class BaseModel(Model):
    class Meta:
        database = db

class Holiday(BaseModel):
    name = CharField(max_length=100, unique=True)
    description = TextField(default="")   # пустая строка вместо NULL
    is_active = BooleanField(default=True)

class NonWorkingDate(BaseModel):
    date = DateField(unique=True)
    is_active = BooleanField(default=True)

class HolidayDate(BaseModel):
    holiday = ForeignKeyField(Holiday, backref='holiday_dates')
    date = ForeignKeyField(NonWorkingDate, backref='holiday_dates')
    is_active = BooleanField(default=True)

    class Meta:
        primary_key = CompositeKey('holiday', 'date')
        # CompositeKey автоматически создаёт уникальность, второй индекс не нужен

def init_db():
    db.connect()
    db.create_tables([Holiday, NonWorkingDate, HolidayDate], safe=True)
    db.close()

if __name__ == '__main__':
    init_db()
    print("База данных инициализирована.")