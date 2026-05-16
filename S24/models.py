from peewee import *

db = SqliteDatabase('room_availability.db')
class BaseModel(Model):
    class Meta:
        database = db
class Room(BaseModel):
    number = CharField(unique=True, max_length=10)
    floor = IntegerField()
    capacity = IntegerField()
class Event(BaseModel):
    title = CharField(max_length=100)
    type = CharField(max_length=50)
class RoomBlock(BaseModel):
    room = ForeignKeyField(Room, backref='blocks', null=False, on_delete='CASCADE')
    event = ForeignKeyField(Event, backref='blocks', null=False, on_delete='CASCADE')
    start_datetime = DateTimeField()
    end_datetime = DateTimeField()
    status = CharField(max_length=20, default='active')
    comment = TextField(default='')
    is_deleted = BooleanField(default=False)
def init_db():
    db.connect()
    db.create_tables([Room, Event, RoomBlock], safe=True)
    db.close()
    print("База данных и таблицы инициализированы.")
if __name__ == "__main__":
    init_db()
