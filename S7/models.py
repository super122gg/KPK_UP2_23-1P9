from peewee import *
from playhouse import validate_range, validate_regexp, validate_one_of, validate_length

db = SqliteDatabase('data.db')

def validate_positive_or_none(value):
    if value is not None and value <= 0:
        raise ValueError("Значение должно быть положительным или None")
    
class BaseModel(Model):
    class Meta:
        database = db

class Groups(BaseModel):
    class Meta:
        db_table = "groups"
    
    id = AutoField()
    year = IntegerField(null=False,validators=[validate_range(2000, 2999)])
    is_active = BooleanField(default=True) 
    tutor_id = IntegerField(null=True, default=None, validators=[validate_positive_or_none]) 
    student_count = IntegerField(default=0, validators=[validate_range(0, 30)])
    cipher_of_the_training_area = CharField(null=False,max_length=8,
        validators=[validate_regexp(r'^\d{2}\.\d{2}\.\d{2}$')]
    )
    number = IntegerField(null=False,validators = validate_range(1, 9999))
    after_class_number = IntegerField(null=False,
        validators=[validate_one_of([9, 11])]
    )
    prefix = CharField(null=False,
        validators=[validate_length(1, 2)]
    )

def init_db():
    db.connect()
    db.create_tables([Groups])
    print("База данных инициализирована")

if __name__ == '__main__':
    init_db()