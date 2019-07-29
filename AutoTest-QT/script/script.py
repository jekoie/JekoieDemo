import os
import random
import traceback
import datetime
from PyQt5.QtCore import  QThread, pyqtSignal
from faker import Faker
import pandas as pd
from communicate.communicate import SerialCommunicate
from ui.mixin import *

fake = Faker('zh_CN')

class Script(QThread):
    sig_data = pyqtSignal(list)
    sig_finish = pyqtSignal(bool)

    def __init__(self, dev: SerialCommunicate, win_idx: int):
        super().__init__()
        self.dev = dev
        self.win_idx = win_idx
        #'线运行标记'
        self.runnig  = True
        #串口数据缓存区
        self.buffer = BytesBuffer(b'\xff')
        #产品文件
        self.xml = XMLParser()
        #帧头 对应 xml  recv项
        self.frameheader_recv_dict = {}
        #记录数据结果
        self.result_list = []

    def stop(self):
        self.runnig = False

    def recv_item_check(self, item, frame):
        frame_data = frame[self.xml.frameheader_length:]
        bytepos = item.get(XMLParser.Abytepos)
        bytepos_list = bytepos.split(',')
        bytedata = BitArray()
        for pos in  bytepos_list:
            bytedata.append('uint:8={}'.format(frame_data[int(pos)]) )

        convert_value = convert(item.get(XMLParser.AConvert), bytedata)
        expected_value = item.get('value', '')
        msg = item.get('msg', '')

        if convert_value == expected_value:
            self.result_list.append([msg, msg, True])
            self.sig_data.emit([msg, msg, True])
        else:
            self.result_list.append([msg, msg, False])
            self.sig_data.emit([msg, msg, False])

    def recv_check(self, frame: bytearray):
        if frame:
            frameheader = frame[:self.xml.frameheader_length]
            if frameheader in self.frameheader_recv_dict:
                recv_item = self.frameheader_recv_dict[frameheader]
                for childItem in recv_item.iterchildren():
                    self.recv_item_check(childItem, frame)

    def run(self):
        try:
            self.frameheader_recv_dict = self.xml.frameheader_recv()
            while self.runnig:
                self.buffer.extend( self.dev.read_available() )
                self.recv_check( self.buffer.currentFrame )
                self.msleep(100)

            # for i in range(random.randrange(30, 100)):
            #     self.sig_data.emit([fake.name(), fake.address(), random.choice([True, False]) ])
            #     self.msleep(100)

            result = random.choice([True, False])
            self.sig_finish.emit(result)
            self.saveResultLocal(result)
        except Exception as e:
            print(traceback.format_exc())
            Config.LOGGER.error(traceback.format_exc())
        finally:
            self.runnig = False

    def saveResultLocal(self, result):
        df = pd.DataFrame(self.result_list, columns=['测试项', '信息', '结果'])
        df = df.replace([True, False], ['PASS', 'FAIL'])

        now = datetime.datetime.now()
        fileDir = os.path.join(Config.TMP_DIR, Config.PRODUCT_MODEL, str(now.year), str(now.month), str(now.day) )
        os.makedirs(fileDir, exist_ok=True)

        fileName = os.path.join(fileDir, '{}_{}_{}{}.xlsx'.format(Config.PRODUCT_MODEL, now.strftime('%Y%m%d_%H%M%S'), result, self.win_idx))
        df.to_excel(fileName)

