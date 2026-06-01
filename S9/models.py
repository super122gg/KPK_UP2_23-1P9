from peewee import *
import datetime

db = SqliteDatabase('student_movement.db')


class BaseModel(Model):
    class Meta:
        database = db


class MovementType(BaseModel):
    class Meta:
        db_table = "movement_types"
    
    name = CharField(max_length=50, unique=True, null=False)
    code = CharField(max_length=30, unique=True, null=False)


class MovementRecord(BaseModel):
    class Meta:
        db_table = "movement_records"
        indexes = (
            (('student_id', 'movement_date', 'movement_type_id'), True),
        )
    
    id = PrimaryKeyField()  # явно объявляем первичный ключ
    student_id = IntegerField(constraints=[Check('student_id > 0')], null=False)
    movement_type_id = ForeignKeyField(MovementType, backref='records', on_delete='CASCADE', 
                                       constraints=[Check('movement_type_id > 0')], null=False)
    movement_date = DateField(constraints=[Check("movement_date <= date('now')")], null=False)
    order_number = CharField(max_length=50, 
                             constraints=[Check("length(order_number) >= 1 AND length(order_number) <= 50")], 
                             null=False)
    is_active = BooleanField(default=True, null=False)


def init_db():
    db.connect()
    db.create_tables([MovementType, MovementRecord], safe=True)
    
    if not MovementType.select().exists():
        MovementType.create(name='Перевод', code='transfer')
        MovementType.create(name='Отчисление', code='expelled')
        MovementType.create(name='Восстановление', code='reinstated')
        MovementType.create(name='Академический отпуск', code='academic_leave')
        MovementType.create(name='Выход из академа', code='academic_leave_end')
    
    print("База данных инициализирована")


if __name__ == '__main__':
    init_db()