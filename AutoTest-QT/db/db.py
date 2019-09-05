from peewee import *
from datetime import datetime

localdb = SqliteDatabase(None)
remotedb = MySQLDatabase(None)

class BaseModel(Model):
    class Meta:
        database = None
        legacy_table_names = False

class User(BaseModel):
    id = AutoField()
    username = CharField()
    password = CharField()

    class Meta:
        database = localdb

def generate_tables(model):
    # return 'production{}'.format(datetime.now().year)
    return 'production'

class ProductionRecord(BaseModel):
    id = AutoField()
    msg = TextField()
    result = CharField()
    model = CharField()
    version = CharField()
    start_time = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])
    end_time = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])
    total_time = IntegerField()

    class Meta:
        table_function = generate_tables

class LocalProductionRecord(ProductionRecord):
    class Meta:
        database = localdb

class RemoteProductionRecord(ProductionRecord):
    class Meta:
        database = remotedb

class Information(Model):
    id = AutoField()
    production_id = ForeignKeyField(ProductionRecord, backref='infos')