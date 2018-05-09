#coding:utf-8
import sys
import time
import re
import os
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
# os.environ['PATH'] = r'E:\router\bin'
os.environ['PATH'] = BIN_PATH

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
        self.driver = webdriver.PhantomJS()
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
    h803.modify_data('')
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
#
# test_ht803()
# # time.sleep(1000)

class ISCOM1016EM(object):
    def __init__(self, url, username='raisecom', password='admin', data={}, timeout=5):
        self.url = url
        self.ip = re.search(r'(\d{1,3}\.){3}\d{1,3}', self.url).group()
        self.username = username
        self.password = password
        self.timeout = timeout
        self.driver = webdriver.Firefox(timeout=120)
        self.driver.set_window_position(100, 100)
        self.driver.set_window_size(800, 600)
        self.data = data
        self.test_status = True
        # self.driver.implicitly_wait(self.timeout)

    def get_login_url(self):
        self.driver.get(self.url)

    def get_url(self, url=''):
        self.driver.get(url)

    def relogin(self):
        self.get_login_url()
        self.login()

    def close(self):
        self.driver.quit()
        self.driver = None

    def clear_arp(self):
        os.system("arp -d")

    def modify_sn(self, flag=False):
        mac, sn = self.data['mac'], self.data['sn']

        url = "http://{}/{}".format(self.ip, 'MACIDFix.htm')
        self.driver.get(url)
        mac_element = self.driver.find_elements_by_css_selector("input[name='MACID']")
        serial_element = self.driver.find_element_by_name("SERIAL")
        yes_element = self.driver.find_elements_by_css_selector("input[value='y']")[0]
        no_element = self.driver.find_elements_by_css_selector("input[value='n']")[0]
        update_elemnt = self.driver.find_element_by_name("Modify")

        serial_element.clear()
        serial_element.send_keys(sn)

        yes_element.click() if flag else  no_element.click()
        for idx, element in enumerate(mac_element):
            element.clear()
            element.send_keys(mac[0+idx*3:2+idx*3])

        update_elemnt.click()

    def reboot_device(self):
        url = "http://{}/{}".format(self.ip, 'resetdevice.htm')
        self.driver.get(url)
        reboot_element = self.driver.find_element_by_name("Reset")
        reboot_element.click()

    def login(self):
        while True:
            if 'your browser does not support frames' in self.driver.page_source:
                time.sleep(1)
                self.get_login_url()
            else:
                break


        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.NAME, "Username"))
        )

        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.NAME, "Password"))
        )

        username = self.driver.find_element_by_name("Username")
        password = self.driver.find_element_by_name("Password")
        submit = self.driver.find_element_by_css_selector("input[type='Submit']")

        username.clear()
        username.send_keys(self.username)

        password.clear()
        password.send_keys(self.password)
        submit.click()

    def verify_message(self, mac='', sn=''):
        self.driver.get(self.url + 'Status.htm')
        mac_element = self.driver.find_elements_by_css_selector("tbody:first-child > tr:nth-child(1) > td:nth-child(2)")[0]
        serial_element = self.driver.find_elements_by_css_selector("tbody:first-child > tr:nth-child(2) > td:nth-child(2)")[0]

        # print mac_element.text, serial_element.text

    def modify_region(self):
        self.driver.get(self.url + 'RegAccess.htm')
        reg_no_element = self.driver.find_element_by_name('RegNO')
        reg_val_element = self.driver.find_element_by_name('RegVAL')
        update_element = self.driver.find_element_by_name('Update')

        reg_no_element.clear()
        reg_no_element.send_keys('1d')
        reg_val_element.clear()
        reg_val_element.send_keys('0000')

        update_element.click()

    def port_status(self):
        self.driver.get(self.url + 'NonAssPort.htm')
        for idx in range(1, 17, 1):
            element = self.driver.find_elements_by_css_selector("input[name='PortNO'][value='{}']".format(idx))[0]
            # print idx, element.is_selected()

    def modify_sn_and_reboot(self):
        try:
            self.relogin()
            self.modify_sn()
            self.reboot_device()
            self.close()
        except Exception as e:
            self.test_status = False

    def run(self):
        try:
            self.relogin()
            self.modify_sn(mac="C8:50:E9:95:7B:EA", sn="101502000351S18505S051P", flag=False)
            self.reboot_device()

            self.clear_arp()
            self.relogin()
            self.verify_message()

            self.modify_region()
            raw_input(u"打开网络测试仪，运行”16Fport”配置文件，观察指示灯状态，重启待测设备")

            self.clear_arp()
            self.relogin()
            self.modify_sn(mac="C8:50:E9:95:7B:EA", sn="101502000351S18505S051P", flag=True)
            self.port_status()
            time.sleep(5)

            self.relogin()
            self.modify_region()
            raw_input(u"用信而泰网络测试仪")

            self.clear_arp()
            self.relogin()
            self.modify_sn(mac="C8:50:E9:95:7B:EA", sn="101502000351S18505S051P", flag=False)
            self.reboot_device()
            self.port_status()
            self.verify_message()


        except Exception as e:
            print traceback.format_exc()
        finally:
            time.sleep(5)
            # self.close()

# dev = ISCOM1016EM("http://192.168.2.1/login2.htm", 'admin', 'raisecom')
# dev.modify_sn_and_reboot()