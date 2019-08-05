import os
import io
import random
import datetime
from PyQt5.QtCore import  QThread, pyqtSignal
from faker import Faker
import pandas as pd
from communicate.communicate import SerialCommunicate
from ui.mixin import *
from db import db

fake = Faker('zh_CN')

@DebugClass
class Script(QThread):
    sig_data = pyqtSignal(list)
    sig_finish = pyqtSignal(bool)

    def __init__(self, dev: SerialCommunicate, win_idx: int):
        super().__init__()
        self.dev = dev
        self.win_idx = win_idx
        #串口数据缓存区
        self.buffer = BytesBuffer(b'\xff')
        #产品文件
        self.xml = XMLParser()
        #帧头 对应 xml  recv项
        self.frameheader_recv_dict = {}
        #记录数据结果
        self.result_list = []
        #
        self.runnig = True

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

    def recv_check(self, frame: bytes):
        if frame:
            frameheader = frame[:self.xml.frameheader_length]
            if frameheader in self.frameheader_recv_dict:
                recv_item = self.frameheader_recv_dict[frameheader]
                for childItem in recv_item.iterchildren():
                    self.recv_item_check(childItem, frame)

    def run(self):
        start_time = datetime.datetime.now()
        self.frameheader_recv_dict = self.xml.frameheader_recv()
        while self.runnig:
            self.buffer.extend( self.dev.read_available() )
            self.recv_check( self.buffer.currentFrame )
            self.msleep(100)

        # for i in range(random.randrange(30, 100)):
        #     self.sig_data.emit([fake.name(), fake.address(), random.choice([True, False]) ])
        #     self.msleep(100)


        result = random.choice([True, False])
        end_time = datetime.datetime.now()
        self.sig_finish.emit(result)
        self.storeTestResult(result, start_time, end_time)

    def storeTestResult(self, result, start_time, end_time):
        df = pd.DataFrame(self.result_list, columns=['测试项', '信息', '结果'])
        df = df.replace([True, False], ['PASS', 'FAIL'])


        msgbuf = io.StringIO()
        df.to_csv(msgbuf, index=False)

        total_time = (end_time - start_time).seconds
        db.remotedb.create_tables([db.RemoteProductionRecord])
        db.RemoteProductionRecord.create(msg=msgbuf.getvalue(), result=result, model=Config.PRODUCT_MODEL, version='1.0',
                                         start_time=start_time, end_time=end_time, total_time=total_time)

        db.localdb.create_tables([db.LocalProductionRecord])
        db.LocalProductionRecord.create(msg=msgbuf.getvalue(), result=result, model=Config.PRODUCT_MODEL, version='1.0',
                                         start_time=start_time, end_time=end_time, total_time=total_time)

