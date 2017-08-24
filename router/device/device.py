#coding:utf-8
import sys
import time
import re
import os
import selenium.common
from lxml import etree
from selenium import webdriver
import pyping
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
reload(sys)
sys.setdefaultencoding('utf-8')
BIN_PATH = os.path.join( os.getcwd(), 'bin')
os.environ['PATH'] =  BIN_PATH

class Device(object):
    __instance = None
    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super(Device, cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self, url, username, password, firmware, timeout=5):
        self.url = url
        self.ip = re.search(r'(\d{1,3}\.){3}\d{1,3}', self.url).group()
        self.username = username
        self.password = password
        self.firmware = firmware
        self.timeout = timeout
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(self.timeout)

    def get_url(self):
        self.driver.set_window_position(100, 100)
        self.driver.set_window_size(800, 600)
        self.driver.get(self.url)

    def relogin(self):
        self.get_url()
        self.login()

    def close(self):
        self.driver.quit()
        self.driver = None

    def wait_device_to_reset(self , time_limit=30):
        def reset():
            ret = True
            packet = pyping.Ping(self.ip, timeout=1000, packet_size=32)
            while ret : ret = packet.do()
            while not ret: ret = packet.do()

        start_time = time.time()
        while True:
            reset()
            if time.time() - start_time > time_limit:
                break

    def modify_data(self, data):
        pass

    def login(self):
        raise NotImplementedError

    def factory_reset(self):
        raise NotImplementedError

    def check_version(self, version):
        raise NotImplementedError

    def upgrade(self):
        raise NotImplementedError

class HT803(Device):
    def __init__(self, url, username, password, firmware, timeout=5):
        Device.__init__(self, url, username, password, firmware, timeout)

    def login(self):
        try:
            self.driver.find_element_by_name('username').send_keys(self.username)
            self.driver.find_element_by_name('password').send_keys(self.password)
            self.driver.find_element_by_name('save').click()
        except Exception as e:
          #  print traceback.format_exc()
            pass

    def upgrade(self):
        code_frame = self.driver.find_element_by_xpath('//frame[@src="code.asp"]')
        self.driver.switch_to.frame(code_frame)

        self.driver.find_element_by_xpath(u'//a/span[text()="系统管理"]/..').click()
        self.driver.find_element_by_xpath('//a[@href="upgrade.asp"]').click()
        self.driver.switch_to.default_content()
        status_frame = self.driver.find_element_by_xpath('//frame[@src="/admin/status.asp"]')
        self.driver.switch_to.frame(status_frame)
        file_upload = self.driver.find_element_by_name('binary')
        submit = self.driver.find_element_by_name('send')

        file_upload.clear()
        file_upload.send_keys(self.firmware)
        submit.click()
        self.driver.switch_to.alert.accept()
        if u'不能升级相同版本的镜像' in self.driver.page_source:
            return  False
        return True

    def factory_reset(self):
        code_frame = self.driver.find_element_by_xpath('//frame[@src="code.asp"]')
        self.driver.switch_to.frame(code_frame)
        self.driver.find_element_by_xpath(u'//a/span[text()="系统管理"]/..').click()
        self.driver.find_element_by_xpath('//a[@href="saveconf.asp"]/..').click()
        self.driver.switch_to.default_content()
        status_frame = self.driver.find_element_by_xpath('//frame[@src="/admin/status.asp"]')
        self.driver.switch_to.frame(status_frame)
        self.driver.find_element_by_xpath(u'//input[@value="重置"]').click()
        self.driver.switch_to.alert.accept()

    def check_version(self, version):
        status_frame = self.driver.find_element_by_xpath('//frame[@src="/admin/status.asp"]')
        self.driver.switch_to.frame(status_frame)

        html = etree.HTML(self.driver.page_source)
        verson_node = html.xpath(u'.//b[text()="软件版本"]/../../following-sibling::*[1]//font')[0]
        if verson_node.text == version:
            return True
        return False


class HT825GP(Device):
    def __init__(self, url, username, password, firmware, timeout=5):
        Device.__init__(self, url, username, password, firmware, timeout)

    def relogin(self):
        def mini_login():
            self.get_url()
            self.login()

        count = 0
        while count < 10:
            try:
                mini_login()
            except Exception as e:
                # print traceback.format_exc()
                pass
            finally:
                time.sleep(3)
                if self.driver.current_url == 'http://192.168.1.1/cumain.html':
                    return
                else:
                    count += 1

    def login(self):
        self.driver.find_element_by_name('username').send_keys(self.username)
        self.driver.find_element_by_name('password').send_keys(self.password)
        self.driver.find_element_by_id('login').click()
        time.sleep(2)
        self.driver.switch_to.alert.accept()
        self.driver.find_element_by_name('username').send_keys(self.username)
        self.driver.find_element_by_name('password').send_keys(self.password)
        self.driver.find_element_by_id('login').click()

    def upgrade(self):
        self.driver.get('http://192.168.1.1/upload.html')
        self.driver.find_element_by_xpath('.//input[@name="filename"]').send_keys(self.firmware)
        self.driver.find_element_by_xpath('.//input[@type="submit"]').click()
        return True

    def factory_reset(self):
        self.driver.get('http://192.168.1.1/resetdefault.html')
        self.driver.find_element_by_xpath(u'.//input[@value="恢复出厂设置"]').click()

    def check_version(self, version):
        self.driver.get('http://192.168.1.1/wan_status.html')

    def modify_data(self, data):
        self.driver.get('http://192.168.1.1/factorymode.html')
        sf_feature = self.driver.find_element_by_id('SfCfgName')
        time.sleep(3)
        sf_feature.clear()
        sf_feature.send_keys(data)
        self.driver.find_element_by_name('save').click()

def test_ht825():
    ht825gp = HT825GP('http://192.168.1.1/login.html', 'cqadmin', 'cqunicom', r'C:\Users\jett\Desktop\bin\ISCOMHT825-GP_Z_UC03_SYSTEM_2.0.0(a)_20160317_R1B01D7970df9e_acf0af12.upf')
    ht825gp.relogin()
    ht825gp.modify_data()
    ht825gp.upgrade()
    ht825gp.wait_device_to_reset()

    ht825gp.relogin()
    ht825gp.factory_reset()
    ht825gp.wait_device_to_reset()

    ht825gp.relogin()
    ht825gp.check_version( '1')


def test_ht803():
    h803 = HT803('http://192.168.1.1/admin/login.asp', 'admin', 'admin', r'C:\Users\jett\Desktop\bin\ISCOMHT803-DR_T_RC01_SYSTEM_3.0.15(a)_20170103')
    h803.relogin()
    h803.modify_data()
    h803.upgrade()
    # h803.wait_device_to_reset()
    #
    # h803.relogin()
    # h803.factory_reset()
    # h803.wait_device_to_reset()
    #
    # h803.relogin()
    # h803.check_version('1')
    # h803.driver.quit()

# test_ht803()
# time.sleep(1000)