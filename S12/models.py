from datetime import datetime
from peewee import (
    SqliteDatabase, Model, AutoField, IntegerField, CharField,
    BooleanField, DateTimeField, Check
)

db = SqliteDatabase('curriculum_plan.db')


class BaseModel(Model):
    class Meta:
        database = db


class CurriculumPlan(BaseModel):
    """Основная сущность: запись учебного плана."""
    id = AutoField(primary_key=True)
    # Поля-идентификаторы без внешних ключей (ID из внешних сервисов)
    specialty_id = IntegerField(constraints=[Check('specialty_id > 0')])
    discipline_id = IntegerField(constraints=[Check('discipline_id > 0')])
    semester = IntegerField(constraints=[Check('semester >= 1 AND semester <= 12')])
    theory_hours = IntegerField(constraints=[Check('theory_hours >= 0')])
    practice_hours = IntegerField(constraints=[Check('practice_hours >= 0')])
    total_hours = IntegerField(constraints=[Check('total_hours >= 0')])
    assessment_type = CharField(max_length=20, constraints=[
        Check("assessment_type IN ('exam', 'credit', 'graded_credit')")
    ])
    year = IntegerField(constraints=[Check('year >= 2000')])
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'curriculum_plans'
        # Уникальность по (specialty_id, discipline_id, semester, year)
        indexes = (
            (('specialty_id', 'discipline_id', 'semester', 'year'), True),
        )

    def save(self, *args, **kwargs):
        """Пересчет total_hours перед сохранением."""
        self.total_hours = self.theory_hours + self.practice_hours
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    @classmethod
    def validate_limit(cls, limit):
        """Проверка лимита."""
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("limit must be an integer between 1 and 100")

    @classmethod
    def validate_positive_int(cls, value, field_name):
        """Проверка положительного целого числа."""
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise ValueError(f"{field_name} must be a positive integer")

    @classmethod
    def validate_non_negative_int(cls, value, field_name):
        """Проверка неотрицательного целого числа."""
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{field_name} must be a non-negative integer")

    @classmethod
    def create_plan(cls, specialty_id, discipline_id, semester, theory_hours,
                    practice_hours, assessment_type, year):
        """Создание нового учебного плана с валидацией."""
        # Валидация обязательных полей
        if not all([specialty_id, discipline_id, semester, theory_hours is not None,
                    practice_hours is not None, assessment_type, year]):
            raise ValueError("All required fields must be provided")

        # Валидация типов и значений
        cls.validate_positive_int(specialty_id, "specialty_id")
        cls.validate_positive_int(discipline_id, "discipline_id")
        cls.validate_positive_int(semester, "semester")
        cls.validate_positive_int(year, "year")
        cls.validate_non_negative_int(theory_hours, "theory_hours")
        cls.validate_non_negative_int(practice_hours, "practice_hours")

        if semester < 1 or semester > 12:
            raise ValueError("semester must be between 1 and 12")

        if year < 2000:
            raise ValueError("year must be >= 2000")

        valid_assessment_types = ['exam', 'credit', 'graded_credit']
        if assessment_type not in valid_assessment_types:
            raise ValueError(f"assessment_type must be one of: {valid_assessment_types}")

        total_hours = theory_hours + practice_hours

        return cls.create(
            specialty_id=specialty_id,
            discipline_id=discipline_id,
            semester=semester,
            theory_hours=theory_hours,
            practice_hours=practice_hours,
            total_hours=total_hours,
            assessment_type=assessment_type,
            year=year
        )

    @classmethod
    def soft_delete(cls, plan_id):
        """Мягкое удаление: is_active = False. Возвращает True если деактивировано, иначе False."""
        if not isinstance(plan_id, int) or plan_id <= 0:
            return False

        updated = cls.update(is_active=False).where(
            (cls.id == plan_id) & (cls.is_active == True)
        ).execute()
        return updated == 1

    @classmethod
    def get_by_id(cls, plan_id):
        """Получить запись по ID (только активные)."""
        if not isinstance(plan_id, int) or plan_id <= 0:
            return None
        return cls.select().where((cls.id == plan_id) & (cls.is_active == True)).first()

    @classmethod
    def get_list(cls, specialty_id=None, discipline_id=None, semester=None,
                 year=None, assessment_type=None, is_active=True, limit=100, offset=0):
        """Получить список записей по фильтрам с пагинацией."""
        # Валидация limit
        cls.validate_limit(limit)

        # Валидация offset
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")

        query = cls.select().where(cls.is_active == is_active)

        if specialty_id is not None:
            cls.validate_positive_int(specialty_id, "specialty_id")
            query = query.where(cls.specialty_id == specialty_id)

        if discipline_id is not None:
            cls.validate_positive_int(discipline_id, "discipline_id")
            query = query.where(cls.discipline_id == discipline_id)

        if semester is not None:
            if not isinstance(semester, int) or semester < 1 or semester > 12:
                raise ValueError("semester must be an integer between 1 and 12")
            query = query.where(cls.semester == semester)

        if year is not None:
            if not isinstance(year, int) or year < 2000:
                raise ValueError("year must be an integer >= 2000")
            query = query.where(cls.year == year)

        if assessment_type is not None:
            valid_types = ['exam', 'credit', 'graded_credit']
            if assessment_type not in valid_types:
                raise ValueError(f"assessment_type must be one of: {valid_types}")
            query = query.where(cls.assessment_type == assessment_type)

        return query.limit(limit).offset(offset)

    @classmethod
    def update_plan(cls, plan_id, theory_hours=None, practice_hours=None, assessment_type=None):
        """Обновление записи (только разрешённые поля) - атомарная операция."""
        # Валидация plan_id
        if not isinstance(plan_id, int) or plan_id <= 0:
            return None

        # Проверяем, существует ли запись и активна ли она
        existing = cls.get_by_id(plan_id)
        if not existing:
            return None

        # Собираем данные для обновления
        data = {}

        if theory_hours is not None:
            cls.validate_non_negative_int(theory_hours, "theory_hours")
            data['theory_hours'] = theory_hours

        if practice_hours is not None:
            cls.validate_non_negative_int(practice_hours, "practice_hours")
            data['practice_hours'] = practice_hours

        if assessment_type is not None:
            valid_types = ['exam', 'credit', 'graded_credit']
            if assessment_type not in valid_types:
                raise ValueError(f"assessment_type must be one of: {valid_types}")
            data['assessment_type'] = assessment_type

        if not data:
            return existing  # Ничего не меняем, возвращаем текущий объект

        # Пересчитываем total_hours, если изменились часы
        if 'theory_hours' in data or 'practice_hours' in data:
            new_theory = data.get('theory_hours', existing.theory_hours)
            new_practice = data.get('practice_hours', existing.practice_hours)
            data['total_hours'] = new_theory + new_practice

        # Атомарное обновление
        data['updated_at'] = datetime.now()

        updated_count = cls.update(data).where(
            (cls.id == plan_id) & (cls.is_active == True)
        ).execute()

        # Возвращаем обновленный объект
        if updated_count > 0:
            return cls.get_by_id(plan_id)
        return None


def init_db():
    """Создание таблиц и заполнение начальными данными"""
    db.connect()
    db.create_tables([CurriculumPlan], safe=True)
    print("База данных curriculum_plan.db успешно инициализирована.")


if __name__ == '__main__':
    init_db()