from peewee import *

db = SqliteDatabase('room_availability.db')

class BaseModel(Model):
    class Meta:
        database = db

class Status(BaseModel):
    name = CharField(unique=True, max_length=20)  
    description = CharField(max_length=100, null=True)

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
    status = ForeignKeyField(Status, backref='blocks', null=False, on_delete='PROTECT')
    start_datetime = DateTimeField()
    end_datetime = DateTimeField()
    comment = TextField(default='')
    is_deleted = BooleanField(default=False)

def init_db():
    db.connect()
    db.create_tables([Status, Room, Event, RoomBlock], safe=True)
    default_statuses = ['active', 'cancelled', 'pending']
    for s_name in default_statuses:
        Status.get_or_create(name=s_name)
    db.close()
    print("БД инициализирована")

if __name__ == "__main__":
    init_db()
