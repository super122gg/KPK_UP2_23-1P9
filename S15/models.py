from peewee import Model, SqliteDatabase, AutoField, IntegerField, BooleanField
from contextlib import closing

db = SqliteDatabase('load_assignment.db')


class LoadAssignment(Model):
    id = AutoField(primary_key=True, column_name='id')
    teacher_id = IntegerField(column_name='teacher_id', null=False)
    discipline_id = IntegerField(column_name='discipline_id', null=False)
    group_id = IntegerField(column_name='group_id', null=False)
    hours_total = IntegerField(column_name='hours_total', null=False)
    is_active = BooleanField(column_name='is_active', default=True, null=False)

    class Meta:
        database = db
        table_name = 'LOAD_ASSIGNMENT'


def init_db():
    with closing(db):
        db.connect()
        db.create_tables([LoadAssignment], safe=True)


if __name__ == '__main__':
    init_db()
