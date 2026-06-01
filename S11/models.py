from peewee import (
    SqliteDatabase,
    Model,
    AutoField,
    CharField,
    IntegerField,
    ForeignKeyField,
)

db = SqliteDatabase("discipline_service.db")


class BaseModel(Model):
    class Meta:
        database = db


class Category(BaseModel):
    """Категория дисциплины."""

    id = AutoField()
    name = CharField(max_length=100, unique=True)
    description = CharField(max_length=255, default="")

    class Meta:
        table_name = "categories"


class Discipline(BaseModel):
    """Дисциплина."""

    id = AutoField()
    name = CharField(max_length=100, unique=True)  # Уникальное название дисциплины
    code = CharField(max_length=20, unique=True)   # Уникальный код дисциплины
    total_hours = IntegerField(constraints=[Check("total_hours > 0")])  # Часов > 0
    category = ForeignKeyField(Category, backref="disciplines", on_delete="RESTRICT", null=False)

    class Meta:
        table_name = "disciplines"


def init_db():
    """Создаёт таблицы в базе данных, если они ещё не существуют."""
    with db:
        # Для проверки constraints нужно включить foreign keys и check constraints
        db.execute_sql("PRAGMA foreign_keys = ON;")
        db.create_tables([Category, Discipline])


if __name__ "__main__":
    init_db()
    print("База данных для Discipline Service инициализирована.")
