from datetime import datetime
from peewee import (
    SqliteDatabase, Model, AutoField, CharField, IntegerField,
    ForeignKeyField, DateTimeField, BooleanField, Check
)

db = SqliteDatabase('campus.db')


class BaseModel(Model):
    class Meta:
        database = db


class City(BaseModel):
    """Справочник городов"""
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True, constraints=[Check("length(name) >= 1")])

    class Meta:
        table_name = 'cities'


class ContactType(BaseModel):
    """Справочник типов контактов: телефон, email, факс и т.д."""
    id = AutoField(primary_key=True)
    name = CharField(max_length=50, unique=True, constraints=[Check("length(name) >= 1")])

    class Meta:
        table_name = 'contact_types'


class Campus(BaseModel):
    """Основная сущность: корпус учебного заведения"""
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True, constraints=[Check("length(name) >= 1")])
    address = CharField(max_length=255, constraints=[Check("length(address) >= 5")])
    city = ForeignKeyField(City, backref='campuses', on_delete='RESTRICT')
    floors = IntegerField(constraints=[Check('floors >= 1')])
    description = CharField(max_length=500, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'campuses'
        indexes = (
            (('address', 'city'), True),  # в одном городе не может быть двух корпусов с одинаковым адресом
        )

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    @classmethod
    def soft_delete(cls, campus_id):
        """Мягкое удаление: is_active = False. Возвращает True если деактивировано, иначе False."""
        updated = cls.update(is_active=False).where(
            (cls.id == campus_id) & (cls.is_active == True)
        ).execute()
        return updated > 0


class CampusContact(BaseModel):
    """Транзитивная таблица: связь многие ко многим между Campus и ContactType"""
    id = AutoField(primary_key=True)
    campus = ForeignKeyField(Campus, backref='contacts', on_delete='CASCADE')
    contact_type = ForeignKeyField(ContactType, backref='campus_contacts', on_delete='RESTRICT')
    value = CharField(max_length=200, constraints=[Check("length(value) >= 1")])

    class Meta:
        table_name = 'campus_contacts'
        indexes = (
            (('campus', 'contact_type'), True),  # у корпуса может быть только один контакт каждого типа
        )


def init_db():
    """Создание таблиц и заполнение начальными данными"""
    db.connect()
    db.create_tables([City, ContactType, Campus, CampusContact], safe=True)

    if not City.select().exists():
        moscow = City.create(name='Москва')
        City.create(name='Санкт-Петербург')

        phone = ContactType.create(name='телефон')
        email = ContactType.create(name='email')
        ContactType.create(name='факс')

        c1 = Campus.create(
            name='Главный корпус',
            address='ул. Ленина, д. 1',
            city=moscow,
            floors=5,
            description='Административный и учебный корпус'
        )
        c2 = Campus.create(
            name='Корпус А',
            address='ул. Мира, д. 10',
            city=moscow,
            floors=3
        )

        CampusContact.create(campus=c1, contact_type=phone, value='+7 (495) 123-45-67')
        CampusContact.create(campus=c1, contact_type=email, value='main@college.ru')
        CampusContact.create(campus=c2, contact_type=phone, value='+7 (495) 987-65-43')


if __name__ == '__main__':
    init_db()
    print("База данных campus.db успешно инициализирована.")