import os
import io
import socket
import logging
from collections import defaultdict
from lxml import etree
from communicate.communicate import SerialCommunicate
from lxml.etree import _ElementTree
from datetime import datetime
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor
from db import db

class Logger(object):
    def __init__(self, name, file, level):
        self.__createLogger(name, file, level)

    def __createLogger(self, loggername, file, loggerlevel):
        self.logger = logging.getLogger(loggername)
        self.logger.setLevel(loggerlevel)
        self.logger.addHandler(self.__createHandler(file))

    def __createHandler(self, file):
        try:
            handler = logging.FileHandler(file)
        except TypeError as e :
            handler = logging.StreamHandler(file)
        handler.setFormatter(self.__createFormatter())
        return handler

    def __createFormatter(self):
        fmt = "%(asctime)s ip:{} level:%(levelname)s file:%(filename)s func:%(funcName)s line:%(lineno)d msg:%(message)s".format(socket.gethostbyname(socket.gethostname()))
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        return formatter

class BaseConfig:
    #配置文件路径
    APP_XML = None
    DEV_XML = None
    CONFIG_XML = None
    PRODUCT_XML = None
    ABOUT_HTML = None

    #解析的文件
    APP_XML_TREE: _ElementTree = None
    DEV_XML_TREE:_ElementTree = None
    CONFIG_XML_TREE: _ElementTree = None
    PRODUCT_XML_TREE: _ElementTree = None

    #产品XML文件是否改变
    PRODUCT_XML_CHANGED = False

    #图片文件路径
    APP_DIR = None
    TMP_DIR = None
    LOGO_IMG = None
    FAIL_IMG = None
    PASS_IMG = None
    WARNING_IMG = None

    #pubsub主题
    TOPIC_STARTTEST = 'TOPIC_STARTTEST'
    TOPIC_EXCEPTION = 'TOPIC_EXCEPTION'

    #程序配置文件变量
    #窗口数量（可变）
    INITWIN_NUM = 1
    #启动时窗口数量（不可变）
    FIXED_WIN_NUM = INITWIN_NUM

    #产品型号
    PRODUCT_MODEL = None
    #显示方式： 分页显示，分屏显示
    SCREEN_MODE = False

    #颜色
    COLOR_GREEN = QColor('#006600')
    COLOR_RED = QColor('#C80000')

    #应用程序信息
    ORGANIZATION = 'bona'
    APP_NAME = 'AutoTest'
    APP_VERSION = '1.0'
    APP_AUTHOR = '宝乐深圳研发部-测试组'
    APP_COMPANY = '广东宝乐机器人股份有限公司'
    APP_COPYRIGHT = 'Copyright (c) 2016-{} {} 版权所有'.format(datetime.now().year, APP_COMPANY)
    APP_DESCRIPTION = '上位机自动化测试软件'
    APP_WEBSITE = 'http://www.robotbona.com/?ch.html'

    DEBUG_HANDLER = io.StringIO()
    LOGGER = Logger( __name__ , DEBUG_HANDLER, logging.DEBUG).logger

    #RC {0:{'win':'', 'page':'', 'dev':''}, 'tab':'' }
    RC = defaultdict(dict)

    #QSettings
    QSETTING = QSettings(ORGANIZATION, APP_NAME)

    #远程数据库，记录生产记录
    REMOTE_LOG_DB = 'bona'
    REMOTE_LOG_IP = '127.0.0.1'
    REMOTE_LOG_USER = 'root'
    REMOTE_LOG_PASSWORD = 'test'
    REMOTE_LOG_PORT = 3306
    REMOTE_LOG_CHARSET = 'utf8'

    #本地数据库
    LOCAL_LOG_DB = None

#程序配置类
class Config(BaseConfig):

    @classmethod
    def initialize(cls):
        cls.APP_DIR = os.path.dirname( os.path.dirname(__file__) )
        cls.TMP_DIR = os.path.join(cls.APP_DIR, 'tmp')
        cls.APP_XML = os.path.join(cls.APP_DIR, 'setting', 'app.xml')
        cls.DEV_XML = os.path.join(cls.APP_DIR, 'setting', 'dev.xml')
        cls.CONFIG_XML = os.path.join(cls.APP_DIR, 'setting', 'config.xml')
        cls.ABOUT_HTML = os.path.join(cls.APP_DIR, 'setting', 'about.html')

        cls.LOGO_IMG = os.path.join(cls.APP_DIR, 'image', 'logo.png')
        cls.PASS_IMG = os.path.join(cls.APP_DIR, 'image', 'pass.png')
        cls.FAIL_IMG = os.path.join(cls.APP_DIR, 'image', 'fail.png')
        cls.WARNING_IMG = os.path.join(cls.APP_DIR, 'image', 'warning.png')

        cls.LOCAL_LOG_DB = os.path.normpath(os.path.join(cls.TMP_DIR, 'bona.db'))

        cls.initialize_xml()
        cls.initialize_variable()
        cls.initialize_device()
        cls.initialize_database()

    @classmethod
    def initialize_xml(cls):
        cls.APP_XML_TREE = etree.parse(cls.APP_XML)
        cls.DEV_XML_TREE = etree.parse(cls.DEV_XML)
        cls.CONFIG_XML_TREE = etree.parse(cls.CONFIG_XML)

    @classmethod
    def initialize_variable(cls):
        Config.RC['tab'] = None
        with AppSettingReader() as reader:
            Config.INITWIN_NUM = int(reader.get('initwinnum', 'value'))
            Config.PRODUCT_MODEL = reader.get('product_model', 'value')
            Config.SCREEN_MODE = eval(reader.get('screen_mode', 'value'))

            Config.FIXED_WIN_NUM = Config.INITWIN_NUM

    @classmethod
    def initialize_device(cls):
        for win_idx in range(Config.INITWIN_NUM):
            dev_item = Config.DEV_XML_TREE.find('//li[@win="{}"]'.format(win_idx))
            dev = SerialCommunicate(**dev_item.attrib)
            dev.connect()
            cls.RC.update({win_idx:{'dev':dev, 'first': True}})

    @classmethod
    def initialize_database(cls):
        # db.remotedb.init(cls.REMOTE_LOG_DB, host=cls.REMOTE_LOG_IP, user=cls.REMOTE_LOG_USER, password=cls.REMOTE_LOG_PASSWORD,
        #                  port=cls.REMOTE_LOG_PORT, charset=cls.REMOTE_LOG_CHARSET)
        # db.remotedb.connect(True)

        db.localdb.init(cls.LOCAL_LOG_DB)
        db.localdb.connect(True)

    @classmethod
    def finalize(cls):
        #保存程序变量 到 config.xml
        with AppSettingReader() as reader:
            reader.set('initwinnum', {'value': str(Config.INITWIN_NUM) })
            reader.set('product_model', {'value': str(Config.PRODUCT_MODEL) })
            reader.set('screen_mode', {'value': str(Config.SCREEN_MODE)} )

        #保存设备配置变量到 dev.xml
        for idx in range(Config.FIXED_WIN_NUM):
            dev = Config.RC[idx].get('dev')
            if dev:
                dev.close()
                dev_item = Config.DEV_XML_TREE.find('//li[@win="{}"]'.format(idx))
                dev_item.attrib.update(dev.get_settings())

        Config.DEV_XML_TREE.write(Config.DEV_XML, encoding='utf-8', pretty_print=True, xml_declaration=True)

        #关闭数据库
        # db.remotedb.close()

#应用程序参数读取类
class AppSettingReader(object):
    __root = None
    __tree = None
    __path = None

    def __init__(self):
        if __class__.__path is None:
            __class__.__path = Config.APP_XML
            __class__.__tree = Config.APP_XML_TREE
            __class__.__root = __class__.__tree.getroot()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        __class__.__tree.write(__class__.__path, encoding='utf-8', pretty_print=True, xml_declaration=True)

    def get(self, tag:str, key:str):
        node = __class__.__root.find(".//*[@name='{}']".format(tag))
        return node.get(key, None)

    def set(self, tag:str, attr:dict):
        node = __class__.__root.find(".//*[@name='{}']".format(tag))
        node.attrib.update(attr)
