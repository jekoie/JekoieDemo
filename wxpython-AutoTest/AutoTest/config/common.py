#coding:utf-8
class Static(object):
    mysql = 'mysql'
    oracle = 'oracle'
    tested = 'tested'
    normal = 'normal'

    #正式日志服务器
    db = {
        'host': '',
        'user': '',
        'passwd': '',
        'name': '',
        'port': '',
        'charset': '',
        'type': ''
    }

    #测试数据库
    test_db = {
        'host': '',
        'user': '',
        'passwd': '',
        'name': '',
        'port': 3306,
        'charset': 'utf8',
        'type': mysql
    }

    #正式MES数据库
    mes_db = {
        'host': '',
        'user': '',
        'passwd': '',
        'name': '',
        'port': 1521,
        'charset': 'utf8',
        'type': oracle
    }

    #测试MES数据库
    mes_test_db = {
        'host': '',
        'user': '',
        'passwd': '',
        'name': '',
        'port': 1521,
        'charset': 'utf8',
        'type': oracle
    }

