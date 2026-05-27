from peewee import *

db = SqliteDatabase("sqlite3.db")

class Base(Model):
    """Базовый класс"""
    id = AutoField(primary_key=True)

    class Meta:
        database = db

class UserData(Base):
    """Модель таблицы UserData"""
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    middle_name = CharField(null=True)
    user_id = IntegerField(unique=True)
    email = CharField(unique=True)
    phone_number = CharField(null=True, unique=True)
    avatar = CharField(null=True)
    notification = BooleanField(default=True)
    is_active = BooleanField(default=True)

def init_db():
    """Подключение БД и создание таблиц"""
    tables = [UserData]
    db.connect()
    db.create_tables(tables) 
    db.close()


if __name__ == '__main__':
    init_db()