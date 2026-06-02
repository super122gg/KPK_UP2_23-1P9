from peewee import SqliteDatabase, Model, CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField
from datetime import datetime
import re

db = SqliteDatabase('faculty_service.db')

class Faculty(Model):
    name = CharField(max_length=100, unique=True, null=False)
    code = CharField(max_length=20, unique=True, null=False)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        table_name = 'faculties'

class Department(Model):
    name = CharField(max_length=200, null=False)
    code = CharField(max_length=20, null=False)
    head_name = CharField(max_length=150, null=False)
    head_cabinet_id = CharField(max_length=3, null=False)   # обязательно, 3 цифры
    head_phone = CharField(max_length=20, null=True)        # исправлено: null=True
    reception_is_active = BooleanField(default=False)
    reception_start = IntegerField(null=True)
    reception_end = IntegerField(null=True)
    created_at = DateTimeField(default=datetime.now)
    is_active = BooleanField(default=True)

    class Meta:
        database = db
        table_name = 'departments'
        indexes = (
            (('name', 'code'), True),
        )

class FacultyDepartment(Model):
    faculty = ForeignKeyField(Faculty, backref='departments', on_delete='CASCADE')
    department = ForeignKeyField(Department, backref='faculties', on_delete='CASCADE')

    class Meta:
        database = db
        table_name = 'faculty_departments'
        indexes = (
            (('faculty', 'department'), True),
        )

    @classmethod
    def add_relation(cls, faculty_id, department_id):
        faculty = Faculty.get_or_none(Faculty.id == faculty_id)
        department = Department.get_or_none(Department.id == department_id)
        if not faculty or not department:
            return False
        cls.get_or_create(faculty=faculty, department=department)
        return True

    @classmethod
    def remove_relation(cls, faculty_id, department_id):
        return cls.delete().where(
            (cls.faculty == faculty_id) & (cls.department == department_id)
        ).execute() > 0

    @classmethod
    def get_departments_by_faculty(cls, faculty_id):
        return [fd.department for fd in cls.select().where(cls.faculty == faculty_id)]

    @classmethod
    def get_faculties_by_department(cls, department_id):
        return [fd.faculty for fd in cls.select().where(cls.department == department_id)]


# ---------- Методы Department (CRUD) ----------
    @classmethod
    def get_by_id(cls, dept_id):
        try:
            obj = cls.get(cls.id == dept_id)
            if not obj.is_active:
                return False
            return obj.to_dict()
        except cls.DoesNotExist:
            return False

    @classmethod
    def get_list(cls, page=1, size=10, name=None):
        if page < 1:
            page = 1
        if size < 1:
            size = 1
        if size > 100:
            size = 100
        query = cls.select().where(cls.is_active == True)
        if name:
            query = query.where(cls.name.contains(name))
        query = query.order_by(cls.id)
        offset = (page - 1) * size
        items = list(query.offset(offset).limit(size))
        return [item.to_dict() for item in items]

    @classmethod
    def delete_by_id(cls, dept_id):
        rows = cls.update(is_active=False).where(cls.id == dept_id).execute()
        return rows > 0

    @classmethod
    def update_by_id(cls, dept_id, **kwargs):
        obj = cls.get_or_none(cls.id == dept_id)
        if not obj or not obj.is_active:
            return False
        for key, value in kwargs.items():
            if key not in ('id', 'created_at', 'is_active'):
                if hasattr(obj, key):
                    # Позволяем установить None для опциональных полей
                    setattr(obj, key, value)
        obj.save()
        return obj.to_dict()

    def save(self, *args, **kwargs):
        # Пустые строки → None для опциональных полей
        if self.head_phone == "":
            self.head_phone = None
        if self.reception_start == "":
            self.reception_start = None
        if self.reception_end == "":
            self.reception_end = None

        # Обязательные поля: name, code, head_name, head_cabinet_id
        if not self.name or self.name.strip() == "":
            raise ValueError("name должен быть непустой строкой")
        if not self.code or self.code.strip() == "":
            raise ValueError("code должен быть непустой строкой")
        if not self.head_name or self.head_name.strip() == "":
            raise ValueError("head_name должен быть непустой строкой")
        if not self.head_cabinet_id or self.head_cabinet_id.strip() == "":
            raise ValueError("head_cabinet_id должен быть непустой строкой")

        # Длины
        if len(self.name) < 2 or len(self.name) > 200:
            raise ValueError("name 2-200 символов")
        if len(self.code) < 2 or len(self.code) > 20:
            raise ValueError("code 2-20 символов")
        if len(self.head_name) < 2 or len(self.head_name) > 150:
            raise ValueError("head_name 2-150 символов")
        if len(self.head_cabinet_id) != 3 or not self.head_cabinet_id.isdigit():
            raise ValueError("head_cabinet_id должен быть ровно 3 цифры")
        if self.head_phone is not None and (len(self.head_phone) < 2 or len(self.head_phone) > 20):
            raise ValueError("head_phone 2-20 символов")

        # Время приёма
        if self.reception_start is not None:
            if not isinstance(self.reception_start, int) or self.reception_start < 0 or self.reception_start > 23:
                raise ValueError("reception_start 0-23")
        if self.reception_end is not None:
            if not isinstance(self.reception_end, int) or self.reception_end < 0 or self.reception_end > 23:
                raise ValueError("reception_end 0-23")
        if self.reception_start is not None and self.reception_end is not None and self.reception_start > self.reception_end:
            raise ValueError("reception_start ≤ reception_end")

        # Уникальность name+code по всем записям (включая неактивные)
        conflict = Department.select().where(
            (Department.name == self.name) & (Department.code == self.code)
        )
        if self.id:
            conflict = conflict.where(Department.id != self.id)
        if conflict.exists():
            raise ValueError("Отделение с таким name и code уже существует")

        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'head_name': self.head_name,
            'head_cabinet_id': self.head_cabinet_id,
            'head_phone': self.head_phone,
            'reception_is_active': self.reception_is_active,
            'reception_start': self.reception_start,
            'reception_end': self.reception_end,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
        }


def init_db():
    db.connect()
    db.create_tables([Faculty, Department, FacultyDepartment], safe=True)
    db.close()

if __name__ == "__main__":
    init_db()
    print("База данных инициализирована")