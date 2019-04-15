import MySQLdb
from oracle import cx_Oracle
from config.common import Static

class BaseDB(object):
    def __init__(self , **kwargs):
        '[host, user, passwd, name, port, charset, type]'
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def connect(self): pass

    def close(self): pass

    def execute(self, sql):pass

    def fetchone(self, sql): pass

    def fetchall(self, sql): pass

    def rollback(self):pass

    def commit(self):pass

    def __str__(self):
        return '{{user:{} passwd:{} at {!s}}}'.format(self.user, self.passwd, self.conn)

class DB(BaseDB):
    def connect(self):
        if self.type == Static.mysql:
            self.conn = MySQLdb.connect(self.host, self.user, self.passwd, self.name, charset=self.charset)
            self.cursor = self.conn.cursor()
        elif self.type == Static.oracle:
            uri = '{0.host}:{0.port}/{0.name}'.format(self)
            self.conn = cx_Oracle.connect(self.user, self.passwd, uri)
            self.cursor = self.conn.cursor()

        self.closed = False

    def close(self):
        self.cursor.close()
        self.conn.close()
        self.closed = True

    def execute(self, sql):
        self.cursor.execute(sql)

    def fetchone(self, sql):
        if self.type == Static.mysql:
            self.cursor.execute(sql)
            return self.cursor.fetchone()
        return self.cursor.execute(sql).fetchone()

    def fetchall(self, sql):
        if self.type == Static.mysql:
            self.cursor.execute(sql)
            return self.cursor.fetchall()
        return self.cursor.execute(sql).fetchall()

    def rollback(self):
        self.conn.rollback()

    def commit(self):
        self.conn.commit()

