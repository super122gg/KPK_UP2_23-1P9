from peewee import SqliteDatabase, Model, CharField, IntegerField, BooleanField, ForeignKeyField, AutoField

db = SqliteDatabase('permissions.db')

class Permission(Model):
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True, null=False)
    description = CharField(max_length=255, null=True, default='')
    is_active = BooleanField(null=False, default=True)

    class Meta:
        database = db
        table_name = 'permissions'

class RolePermission(Model):
    id = AutoField(primary_key=True)
    role_id = IntegerField(null=False)
    permission = ForeignKeyField(Permission, backref='role_permissions', on_delete='CASCADE')

    class Meta:
        database = db
        table_name = 'role_permissions'
        indexes = (
            (('role_id', 'permission'), True),
        )

def init_db():
    db.connect()
    db.create_tables([Permission, RolePermission], safe=True)
    db.close()

if __name__ == "__main__":
    init_db()
    print("База данных permissions.db успешно создана")