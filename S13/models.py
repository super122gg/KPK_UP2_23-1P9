from peewee import (
    Model,
    AutoField,
    IntegerField,
    CharField,
    TextField,
    BooleanField,
    DateTimeField,
    SqliteDatabase,
)
from datetime import datetime

db = SqliteDatabase("work_program_service.db")


class BaseModel(Model):
    class Meta:
        database = db


class WorkProgram(BaseModel):
    id = AutoField()
    discipline_id = IntegerField()
    specialty_id = IntegerField()
    title = CharField(max_length=255)
    file_url = CharField(max_length=512)
    file_size_bytes = IntegerField(null=True)
    version = CharField(max_length=50, default="1.0")
    description = TextField(null=True)
    uploaded_by_user_id = IntegerField()
    uploaded_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    is_active = BooleanField(default=True)

    class Meta:
        table_name = "work_program"
        indexes = (
            (("discipline_id", "specialty_id", "version"), True),
        )


def init_db():
    with db:
        db.create_tables([WorkProgram])


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")