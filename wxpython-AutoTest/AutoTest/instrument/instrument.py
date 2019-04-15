import io
import os
import psutil
import time
import ftputil
import traceback
from ui import tool
from lxml import etree
from config.config import Config

class TeleATT(object):
    tongwei_cache = ''
    product_flag = ''
    modify_flag = False
    def __init__(self, product, item=None):
        self.item = item
        self.product = product

        self.encoding = 'gb2312'
        self.ftpaddr = '192.168.60.70'
        self.ftpuser = 'anonymous'
        self.ftppasswd = 'anonymous'

        self.tongwei = ''
        self.teleattcfg = ''
        self.product_dir = ''
        self._prepare()

    def _findProcByName(self, name):
        for proc in psutil.process_iter():
            if name.lower() in proc.name().lower():
                return proc
        return None

    def _prepare(self):
        orign = 'ftp://{}'.format(self.ftpaddr)
        self.product_dir = self.product.xml.dir.replace(orign, '.')
        if self.item is not None:
            self.tongwei =  self.item.get('tongwei', 'tongwei1.txt')
            self.teleattcfg = self.item.get('telecfg', 'TeleATTCfg')

    def run(self):
        self.modify_teleappconfig()
        self.startup_teleapp( self.download_TeleATTCfg()   )

        self.enterWorkingDir()
        self.clear_files()
        self.write_tongwei()
        result = self.poll_result()
        self.clear_files()

        return result

    def enterWorkingDir(self):
        os.chdir(Config.tmp)

    def _startup_app(self):
        os.startfile(Config.teleatt)
        try:
            from pywinauto.application import Application
            app = Application().connect(title_re='Version Choose', timeout=3)
            app.top_window().set_focus()
            app.top_window().OK.click()
            app.window(title_re="TeleATT").minimize()
        except Exception:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    def startup_teleapp(self, restart=False):
        if restart:
            proc = self._findProcByName('TeleATT')
            if proc:
                proc.terminate()
            # os.startfile(Config.teleatt)
            self._startup_app()
        else:
            proc = self._findProcByName('TeleATT')
            if proc is None:
                self._startup_app()
                # os.startfile(Config.teleatt)

    def modify_teleappconfig(self):
        if not self.__class__.modify_flag:

            opts = {'InteractionEnabled': 'True', 'FilePath': Config.tmp, 'AutoLoadEnabled': 'True', 'LoadFilePath': Config.tmp,
                    'ResultWinEnable':'False'}
            parser = etree.XMLParser(encoding=self.encoding, remove_blank_text=True, remove_comments=False)
            tree = etree.parse(Config.teleattcfg, parser)
            root = tree.getroot()

            for tagname, value in opts.iteritems():
                tag = root.find(tagname)
                tag.text = value

            tree.write(Config.teleattcfg, encoding=self.encoding, pretty_print=True)
            self.__class__.modify_flag = True

            return True

        return False

    def poll_result(self):
        barcode1, result, content = 'barcode1.txt', False, ''
        while self.product._keepgoing:
            if os.path.exists(barcode1):
                with io.open(barcode1, 'rb') as f:
                    lines = f.readlines()
                    content = ''.join(lines)
                    result = True if 'pass' in lines[1].lower() else False
                break
            else:
                time.sleep(1)

        return result, content

    def download_TeleATTCfg(self):
        if self.product_dir != self.__class__.product_flag:
            with ftputil.FTPHost(self.ftpaddr, self.ftpuser, self.ftppasswd) as host:
                host.chdir(self.product_dir)
                host.download(self.teleattcfg, os.path.join(Config.tmp, 'TeleATTCfg'))
            self.__class__.product_flag = self.product_dir
            return True
        return False

    def download_tongwei(self):
        with ftputil.FTPHost(self.ftpaddr, self.ftpuser, self.ftppasswd) as host:
            host.chdir(self.product_dir)
            host.download(self.tongwei, os.path.join(Config.tmp, 'tongwei1.txt'))

        if os.path.exists(os.path.join(Config.tmp, 'tongwei1.txt')):
            with io.open('tongwei1.txt', mode='rb' ) as f:
                self.__class__.tongwei_cache = f.read()

    def write_tongwei(self):
        if self.__class__.tongwei_cache:
            with io.open('tongwei1.txt', mode='wb') as f:
                f.write(self.__class__.tongwei_cache)
        else:
            self.download_tongwei()

    def clear_files(self):
        barcode1, pretest1, tongwei1 = 'barcode1.txt', 'pretest1.txt', 'tongwei1.txt'
        if os.path.exists(barcode1):
            os.remove(barcode1)
        if os.path.exists(pretest1):
            os.remove(pretest1)
        if os.path.exists(tongwei1):
            os.remove(tongwei1)