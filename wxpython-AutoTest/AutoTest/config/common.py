#coding:utf-8
class Static(object):
    mysql = 'mysql'
    oracle = 'oracle'
    tested = 'tested'
    normal = 'normal'

    #正式日志服务器
    db = {
        'host': '192.168.60.52',
        'user': 'raisecom',
        'passwd': 'raisecom@666',
        'name': 'raisecom',
        'port': 3306,
        'charset': 'utf8',
        'type': mysql
    }

    #测试数据库
    test_db = {
        'host': '192.168.60.52',
        'user': 'raisecom',
        'passwd': 'raisecom@666',
        'name': 'raisecom_test',
        'port': 3306,
        'charset': 'utf8',
        'type': mysql
    }

    #正式MES数据库
    mes_db = {
        'host': '192.168.60.241',
        'user': 'geekinterface',
        'passwd': 'pass@123^&*',
        'name': 'raisecom',
        'port': 1521,
        'charset': 'utf8',
        'type': oracle
    }

    #测试MES数据库
    mes_test_db = {
        'host': '192.168.60.23',
        'user': 'dmsnew_copy',
        'passwd': 'pass',
        'name': 'raisecom',
        'port': 1521,
        'charset': 'utf8',
        'type': oracle
    }

