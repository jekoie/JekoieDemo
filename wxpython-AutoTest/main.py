# coding=utf-8
import os
import wx
import sys
import ftputil
import MySQLdb
import io
import base64
import collections
import logging
import traceback
from app.singleapp import main as singleapp
from app.doubleapp import main as doubleapp
from app import __version__
from app.oracle import cx_Oracle
from app.common import feature

reload(sys)
sys.setdefaultencoding('utf-8')

#app 全局变量
APPCONFIG = {
    'mes_conn':'',
    'mes_cursor':'',
    'log_conn':'',
    'log_cursor':'',

    #路径
    'setting_dir': os.path.join(os.getcwd(), 'setting'),
    'doc_dir': os.path.join(os.getcwd(), 'doc'),
    'tool_dir': os.path.join(os.getcwd(), 'tool'),
    'image_dir':os.path.join(os.getcwd(), 'image'),

    'iconpath': os.path.join(os.getcwd(), 'image', 'logo.ico') ,
    'appsetting_file': os.path.join(os.getcwd(), 'setting' ,'AutoSetting.xml'),
    'setting_file':os.path.join(os.getcwd(), 'setting', 'setting.xml'),
    'config_file': os.path.join(os.getcwd(), 'setting', 'config.xml'),
    'ftp_base_config_dir_admin': u"工艺工作文件夹/工艺资料/AutoTest-Config",
    'ftp_base_config_dir_anonymous': "ftp://192.168.60.70/AutoTest-Config/",

    'debug_handle':io.StringIO(),
    'process_handle':io.StringIO(),
    #MES字典
    'mes_attr':{ 'extern_StationCode':'SZ000', 'extern_SubLineCode':'', 'extern_WJTableName':'BJWORK000000',
            'extern_SubID':0, 'extern_repair': u'未维修', 'extern_QualityFlag': 'no', 'extern_ScanType': u'正常生产', 'op_workers': -1},
    # #测试账号权限
    'testing_account_right': False,
    #维修账号权限
    'repaire_account_right':False,
    #程序模式，单串口，双串口
    'mode': 'single',
    #调试模式
    'debug_mode': False,
    #维修模式
    'repaire_mode': False,
    #使用协议
    'protocol': 'serial',
    #初始窗口数量，只对telnet有效
    'initwinnum': 2,
    #SN自动弹框标记
    'popup_sn_flag':True,
    #工序弹窗标记
    'workstage_flag':False,
    #变量查询窗口，所用的变量
    'var_im':{},
    #启动MES功能的变量,单台过站
    'mes_switch':False,
    #SN自动轮询弹窗对象，
    'popupobj': collections.OrderedDict(),
    #提示信息，只提示一次
    'tip_once': {'hadrun':False},
    #工单号是否加载
    'worktable_loaded':False,
    #工单号是否改变
    'worktable_had_changed':True,
    #产品的配置文件
    'product_xml':(None, None),
    ##工号
    'wn':'000000',
    #员工姓名
    'wn_name': '',
    #老化时间
    'agingtime':12,
    #是否弹出MAC框
    'show_mac':True,
    #工序弹框标记位，初始只弹一次
    'workstage_popup_once_flag': True,
    #选择的是哪个工序
    'station_name': '',
    #工单在测试线可用的SN
    'available_sn':[],
    'logger':None,
    #测试日志服务器
    'log_db_username_testdb': 'raisecom',
    'log_db_password_testdb': 'raisecom@666',
    'log_db_dbname_testdb': 'raisecom_test',
    'log_db_serverip_testdb': '192.168.60.52',
    #正式日志服务器
    'log_db_username': 'raisecom',
    'log_db_password': 'raisecom@666',
    'log_db_dbname': 'raisecom',
    'log_db_serverip': '192.168.60.52',

    #测试数据库账号
    'mes_db_username_testdb': 'ZG1zbmV3X2NvcHk=',
    'mes_db_password_testdb':'cGFzcw==',
    'mes_db_uri_testdb':'MTkyLjE2OC42MC4yMzoxNTIxL3JhaXNlY29t',

    #正式数据库账号
    'mes_db_username': 'Z2Vla2ludGVyZmFjZQ==',
    'mes_db_password': 'cGFzc0AxMjNeJio=',
    'mes_db_uri': 'MTkyLjE2OC42MC4yNDE6MTUyMS9yYWlzZWNvbQ==',
}

class App(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def OnInit(self):
        self.prepare()
        if self.connect_db() == False: return False
        if self.upgrade_software(): return False
        self.get_app()(APPCONFIG)
        return True

    def get_app(self):
        with feature.AppSettingReader(APPCONFIG['appsetting_file']) as s:
            APPCONFIG['mode'] = s.get('mode', 'value')
            APPCONFIG['protocol'] = s.get('protocol', 'value')
            APPCONFIG['initwinnum'] = s.get('initwinnum', 'value')

        if APPCONFIG['mode'] == "single":
            app = singleapp.main
        elif APPCONFIG['mode'] == "double":
            app = doubleapp.main
        return app

    def connect_db(self):
        try:
            mes_username = base64.b64decode(APPCONFIG['mes_db_username'])
            mes_password = base64.b64decode(APPCONFIG['mes_db_password'])
            mes_uri = base64.b64decode(APPCONFIG['mes_db_uri'])
            APPCONFIG['mes_conn'] = cx_Oracle.connect(mes_username, mes_password, mes_uri)
            APPCONFIG['mes_cursor'] = APPCONFIG['mes_conn'].cursor()

            APPCONFIG['log_conn'] = MySQLdb.connect(APPCONFIG['log_db_serverip'], APPCONFIG['log_db_username'],
                                                    APPCONFIG['log_db_password'], APPCONFIG['log_db_dbname'], charset='utf8')
            APPCONFIG['log_cursor'] = APPCONFIG['log_conn'].cursor()
        except MySQLdb.OperationalError as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
            wx.MessageBox(u'连接日志数据库失败', u'{}'.format(e))
            return False
        except cx_Oracle.DatabaseError as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
            wx.MessageBox(u'连接MES数据库失败', u'{}'.format(e))
            return False
        else:
            return True

    def prepare(self):
        if not os.path.exists(APPCONFIG['setting_dir']):
            os.makedirs(APPCONFIG['setting_dir'])
        if not os.path.exists(APPCONFIG['setting_file']):
            feature.generate_setting_file(APPCONFIG['setting_file'])
        if not os.path.exists(APPCONFIG['appsetting_file']):
            with ftputil.FTPHost('192.168.60.70', 'anonymous', 'anonymous') as remote:
                remote.download('/AutoTest-Config/AutoSetting.xml', APPCONFIG['appsetting_file'])

        #初始化串口可用数量
        feature.AvailablePort.get(appconfig=APPCONFIG)
        APPCONFIG['logger'] = feature.Logger(__name__, APPCONFIG['debug_handle'], logging.DEBUG).logger
        if not feature.time_sync():
            wx.MessageBox(u'同步服务器(192.168.60.70)时间失败', 'Warning', style=wx.OK | wx.ICON_EXCLAMATION)

    def upgrade_software(self):
        need_update = False
        try:
            APPCONFIG['log_cursor'].execute("select softname, author, version, path from soft_table where softname=\"{}\"".format(singleapp.__appname__))
            soft_value = APPCONFIG['log_cursor'].fetchone()
            if soft_value is not None:
                softname, author, version, path = soft_value
                if version > __version__:
                    wx.MessageBox(u'发现新版本{}{}, {}'.format(softname, version, path) ,u'升级软件', style=wx.OK|wx.ICON_WARNING)
                    need_update = True
        except Exception as e:
            need_update = False
        finally:
            return need_update

if __name__ == '__main__':
    App()



