#coding:utf-8
import sys
import time
import re
import os
import six
from selenium import webdriver
import pyping
import urllib
import traceback
import inspect
import threading
from functools import wraps
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common import exceptions
from selenium.webdriver.support import expected_conditions as EC

reload(sys)
sys.setdefaultencoding('utf-8')

class VerifyError(Exception):
    def __init__(self, msg):
        self.message = msg

class Monitor(object):
    def __init__(self, cls):
        self.cls = cls

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.cls._event.is_set():
                raise VerifyError()

            if args:
                instance = args[0]
                if isinstance(instance, self.cls):
                    ping = pyping.Ping(instance.ip, timeout=1000, packet_size=32)
                    while True:
                        ret = ping.do()
                        if ret:
                            break
            value = func(*args, **kwargs)
            return value
        return wrapper

class DeviceMeta(type):
    def __init__(self, name, bases, attrs):
        super(DeviceMeta, self).__init__(name, bases, attrs)

        self._event = threading.Event()
        for name, value in attrs.items():
            if not name.startswith('_') and inspect.isfunction(value):
                value = Monitor(self)(value)
                setattr(self, name, value)

@six.add_metaclass(DeviceMeta)
class Device(object):
    driver = None
    _event = threading.Event()
    def __new__(cls, *args, **kwargs):
        if cls.driver is None:
            cls.driver = webdriver.Chrome()
        try:
            v = cls.driver.window_handles
        except exceptions.WebDriverException:
            cls.driver = webdriver.Chrome()

        cls._event.clear()
        return super(Device, cls).__new__(cls, *args, **kwargs)

    def __init__(self, url, username, password, config, statuspanel, timeout=5, **kwargs):
        '''【 url, username, password, config, timeout】'''

        self.url = url
        self.username = username
        self.password = password
        self.config = config
        self.timeout = timeout
        self.statuspanel = statuspanel

        self.prefix = re.search(r'(http.+?//)', self.url).group()
        self.ip = re.search(r'(\d{1,3}\.){3}\d{1,3}', self.url).group()
        self.base_url = '{}{}'.format(self.prefix, self.ip)

        self.driver.implicitly_wait(self.timeout)
        self.driver.set_window_position(100, 100)
        self.driver.set_window_size(800, 600)

        self.statuspanel.setbackgroundcolour(self.config.color_aqua)
        self.statuspanel.setstatus('初始化')
        self.wait = WebDriverWait(self.driver, 60)

    #登录
    def login(self):
        self.statuspanel.setstatus('登录')

    #重新登录
    def relogin(self):
        self.statuspanel.setstatus('重新登录')
        self.home()
        self.login()

    #主页
    def home(self):
        self.statuspanel.setstatus('主页')
        self.driver.get(self.url)

    #根据路径获取相应页面
    def get_by_path(self, path=''):
        url = urllib.basejoin(self.base_url, path)
        self.driver.get(url)

    #修改数据
    def modify_data(self):
        self.statuspanel.setstatus('修改数据')

    #版本校验
    def check_version(self):
        self.statuspanel.setstatus('版本校验')

    #软件升级
    def upgrade_firmware(self):
        self.statuspanel.setstatus('软件升级')

    #恢复出厂设置
    def factory_reset(self):
        self.statuspanel.setstatus('恢复出厂设置')

    #停止
    def stop(self, msg='停止'):
        self.__class__._event.set()
        self.statuspanel.setbackgroundcolour(self.config.color_red)
        self.statuspanel.setstatus(msg)
        self.statuspanel.setresult(self.config.fail)

    #执行体
    def run(self):
        raise NotImplementedError('must be implemented')

class ISCOM1016EM(Device):
    def login(self):
        while True:
            if 'your browser does not support frames' in self.driver.page_source:
                time.sleep(1)
                self.home()
            else:
                break

        username = self.wait.until(
            EC.presence_of_element_located((By.NAME, "Username"))
        )

        password = self.wait.until(
            EC.presence_of_element_located((By.NAME, "Password"))
        )

        submit = self.driver.find_element_by_css_selector("input[type='Submit']")

        username.clear()
        username.send_keys(self.username)

        password.clear()
        password.send_keys(self.password)
        submit.click()

    def modify_data(self, flag=False):
        self.get_by_path('MACIDFix.htm')
        status_msg = '隔离设置设置(YES)' if flag else '隔离设置设置(NO)'
        self.statuspanel.setstatus(status_msg)

        mac_element = self.driver.find_elements_by_css_selector("input[name='MACID']")
        serial_element = self.driver.find_element_by_name("SERIAL")
        yes_element = self.driver.find_elements_by_css_selector("input[value='y']")[0]
        no_element = self.driver.find_elements_by_css_selector("input[value='n']")[0]
        update_elemnt = self.driver.find_element_by_name("Modify")

        serial_element.clear()
        serial_element.send_keys(self.config.sn)

        yes_element.click() if flag else  no_element.click()
        for idx, element in enumerate(mac_element):
            element.clear()
            element.send_keys(self.config.mac[0+idx*3:2+idx*3])

        update_elemnt.click()

        reset_element = self.wait.until(EC.presence_of_element_located((By.NAME, 'Reset')))
        reset_element.click()


    def check_version(self):
        self.statuspanel.setstatus('出厂信息查询')
        self.get_by_path('Status.htm')
        mac_element = self.driver.find_elements_by_css_selector("tbody:first-child > tr:nth-child(1) > td:nth-child(2)")[0]
        serial_element = self.driver.find_elements_by_css_selector("tbody:first-child > tr:nth-child(2) > td:nth-child(2)")[0]

        if mac_element.text.upper() != self.config.mac or serial_element.text.upper() != self.config.sn:
            raise VerifyError('版本校验错误')

    def modify_region(self):
        self.statuspanel.setstatus('寄存器数值设置')
        self.get_by_path('RegAccess.htm')
        reg_no_element = self.driver.find_element_by_name('RegNO')
        reg_val_element = self.driver.find_element_by_name('RegVAL')
        update_element = self.driver.find_element_by_name('Update')

        reg_no_element.clear()
        reg_no_element.send_keys('1d')

        reg_val_element.clear()
        reg_val_element.send_keys('0000')

        update_element.click()

    def check_port_status(self, flag=False):
        status_msg = '查看端口状态(端口设置YES)' if flag else  '查看端口状态(端口设置NO)'
        self.statuspanel.setstatus(status_msg)
        self.get_by_path('NonAssPort.htm')

        yes_status = [True, True, True, True, True, True, True, True,
                      True, True, True, True, True, True, True, False,
                      ]

        no_status = [False, False, False, False, False, False, False, False,
                     False, False, False, False, False, False, False, False,
                      ]

        os.system("arp -d")
        port_status = yes_status if flag else no_status
        for idx in range(1, 17, 1):
            element = self.driver.find_elements_by_css_selector("input[name='PortNO'][value='{}']".format(idx))[0]
            if element.is_selected() != port_status[idx-1]:
                raise VerifyError('端口校验错误')

    def run(self):
        try:
            self.relogin()
            self.modify_data()

            self.relogin()
            self.check_version()

            self.modify_region()
            self.relogin()

            self.modify_data(True)
            self.relogin()
            self.check_port_status(True)

            self.modify_data(False)
            self.relogin()
            self.check_port_status(False)

            self.check_version()

        except VerifyError as e:
            self.stop(e.message)
        except Exception as e:
            self.stop(e.message)
            self.statuspanel.settraceback(traceback.format_exc())
        else:
            self.statuspanel.setbackgroundcolour(self.config.color_green)
            self.statuspanel.setresult(self.config.pass_)
