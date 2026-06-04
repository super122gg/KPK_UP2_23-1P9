from peewee import (
    Model,
    AutoField,
    IntegerField,
    CharField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    SqliteDatabase,
)
from datetime import datetime

db = SqliteDatabase("auth_service.db")


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = AutoField()
    login = CharField(max_length=150, unique=True)
    password_hash = CharField(max_length=255)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "user"


class PasswordResetToken(BaseModel):
    id = AutoField()
    user_id = ForeignKeyField(User, backref="reset_tokens", column_name="user_id")
    token = CharField(max_length=255, unique=True)
    expires_at = DateTimeField()
    is_used = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "password_reset_token"


def init_db():
    with db:
        db.create_tables([User, PasswordResetToken])


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")