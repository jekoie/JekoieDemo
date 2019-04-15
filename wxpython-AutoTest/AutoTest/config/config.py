#coding:utf-8
import io
import os
import wx
import logging
import socket
import enum
import threading
import traceback
from collections import defaultdict
from db import db
from collections import OrderedDict
from common import Static
from lxml import etree

class DeviceState(enum.Enum):
    #设备状态
    foreground = 'foreground'
    background = 'background'

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

class BaseConfig(object):
    db = None
    mes_db = None
    #设备配置文件路径
    devfile = None
    #app配置文件路径
    appfile = None
    #产品配置文件索引
    configfile = None
    #logo文件路径
    logofile = None
    #crc_cal文件路径
    crcfile = None
    #tmp文件路径
    tmp = None
    #ftp基路径
    ftpbase = "工艺工作文件夹/工艺资料/AutoTest-Config"
    #ftp anonymous 基路径
    ftpbase_anonymous = "ftp://192.168.60.70/AutoTest-Config/"

    #初始MES属性
    mes_attr = {'extern_StationCode': 'unset', 'extern_SubLineCode': 'unset', 'extern_WJTableName': 'BJWORK000000',
                'extern_SubID': 0, 'extern_repair': u'未维修', 'extern_QualityFlag': 'no', 'extern_ScanType': u'正常生产',
                'op_workers': 1}

    #异常信息handler
    debughandler = io.StringIO()
    #运行信息handler
    processhandler = io.StringIO()
    
    #权限
    right = {'test_right':False, 'workorder_right': False ,'repaire_right':False}
    #程序模式，单串口，双串口, 调试，维修
    mode = {'mode':'single', 'debug_mode':False, 'repaire_mode':False, 'workorder_mode': True}
    #使用协议（Telnet, Serial）
    protocol =  'serial'
    #初始窗口数量
    initwinnum = 1
    #mes区域是否显示
    showmesarea = False
    #SN自动弹框
    autosn = False
    #工序自动弹框
    autoworkstage = False
    # 工序弹框标记位，初始只弹一次
    workstage_first = True
    #运行变量
    vars = {}
    #记录SN自动弹窗状态
    popup = OrderedDict()
    #工单号是否加载
    worktable_loaded = False
    # 工单号是否改变(保证工单只加载一次)
    worktable_changed = False
    #工号
    wn = '000000'
    #工号对应的员工姓名
    wnname = ''
    #老化时间
    agetime = 12
    #产品配置文件 (xml, product_name)
    product_xml =(None, None)
    #工序号
    station_id = None
    #弹框自动定位
    autopos = False
    #定位偏移x
    posx = 0
    #定位偏移y
    posy = 0
    #信儿泰程序目录
    teledir = ''
    #信儿泰程序路径
    teleatt = ''
    #信儿泰程序配置路径
    teleattcfg = ''

    #logger
    logger = Logger( __name__ , debughandler, logging.DEBUG).logger

    #换行符
    linefeed_none = ''
    linefeed_lf = '\n'
    linefeed_cr = '\r'
    linefeed_crlf = '\r\n'

    #颜色
    colour_red = wx.Colour(249, 0, 0)
    colour_green = wx.Colour(0, 249, 0)
    colour_white = wx.Colour(255, 255, 255)
    colour_black = wx.Colour(0, 0, 0)
    colour_gray = wx.Colour(127, 127, 127)
    colour_aqua = wx.Colour(32, 178, 170)

    #xml parser
    parser_without_comments = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
    parser_with_comments = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=False)
    #设备字典 {0: {'master': [device, status], 'slave':[device, status] }}
    devices = defaultdict(dict)
    #窗口 {'devicewindow':('pagewindow1, pagewindow2)}
    windows = {}
    #线程锁
    lock = threading.RLock()

    #程序版本
    __appname__ = 'AutoTest'
    __version__ = '4.01.7'
    __author__ = 'chenjie'

    #消息主题
    topic_db_change = 'topic_db_change'
    topic_set_window = 'topic_set_window'
    topic_thread_dialog = 'topic_thread_dialog'
    topic_notify_mesarea = 'topic_notify_mesarea'

class Config(BaseConfig):
    #获取设备窗口by页窗口
    @classmethod
    def getdevwin(cls, pagewin):
        for devwin, pagewins in cls.windows.iteritems():
            if pagewin in pagewins:
                return devwin
        return None

    #idx 页编号
    @classmethod
    def getdevice(cls, idx):
        try:
            if Config.mode['mode'] == 'single':
                return Config.devices[idx]['master']
            else:
                return Config.devices[divmod(idx, 2)[0] ]['slave' if divmod(idx, 2)[1] else 'master']
        except Exception as e:
            return None, None

    @classmethod
    def update_device_status(cls, idx, status):
        try:
            if Config.mode['mode'] == 'single':
                Config.devices[idx]['master'][1] = status
            else:
                Config.devices[divmod(idx, 2)[0]]['slave' if divmod(idx, 2)[1] else 'master'][1] = status
        except Exception:
            errormsg = unicode(traceback.format_exc(), encoding='gbk', errors='ignore')
            Config.logger.error(errormsg)

    @classmethod
    def close(cls):
        cls.closedb()
        cls.closedevice()

    @classmethod
    def closedevice(cls):
        for device in Config.devices.values():
            for child_device in device.values():
                if child_device[0]:
                    child_device[0].close()

    @classmethod
    def closedb(cls):
        if cls.db and cls.mes_db:
            cls.db.close()
            cls.mes_db.close()

    @classmethod
    def connect_normal_db(cls):
        cls.closedb()
        cls.db = db.DB(**Static.db)
        cls.mes_db = db.DB(**Static.mes_db)
        cls.db.connect()
        cls.mes_db.connect()
        cls.mode['debug_mode'] = False

    @classmethod
    def connect_testing_db(cls):
        cls.closedb()
        cls.db = db.DB(**Static.test_db)
        cls.mes_db = db.DB(**Static.mes_test_db)
        cls.db.connect()
        cls.mes_db.connect()
        cls.mode['debug_mode'] = True

    @classmethod
    def switch_db(cls, debug=True):
        if cls.mode['debug_mode'] != debug:
            cls.mode['debug_mode'] = debug
            cls.connect_testing_db() if debug else cls.connect_normal_db()

    @classmethod
    def genfilepath(cls, appdir):
        # 产品配置文件索引
        cls.configfile = os.path.normpath(os.path.join(appdir, 'setting', 'config.xml'))
        # 设备配置文件路径
        cls.devfile = os.path.normpath(os.path.join(appdir, 'setting', 'dev.xml'))
        # app配置文件路径
        cls.appfile = os.path.normpath(os.path.join(appdir, 'setting', 'app.xml'))
        # logo文件路径
        cls.logofile = os.path.normpath(os.path.join(appdir, 'image', 'panda.ico'))
        #crc文件路径
        cls.crcfile = os.path.normpath(os.path.join(appdir, 'tool', 'crc_cal.exe') )
        #tmp文件路径
        cls.tmp = os.path.normpath(os.path.join(appdir, 'tmp') )
        # 信儿泰程序目录
        cls.teledir = os.path.normpath(os.path.join(appdir, 'exe', 'teleapp') )
        # 信儿泰程序路径
        cls.teleatt = os.path.normpath(os.path.join(cls.teledir, 'TeleATT.exe') )
        # 信儿泰程序配置路径
        cls.teleattcfg = os.path.normpath(os.path.join(cls.teledir, 'TeleATT.cfg') )



