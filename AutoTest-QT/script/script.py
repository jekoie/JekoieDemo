import os
import io
import random
import datetime
from PyQt5.QtCore import  QThread, pyqtSignal
from faker import Faker
import pandas as pd
from communicate.communicate import SerialCommunicate
from ui.mixin import *
from . import mix
from db import db
from lxml import etree

fake = Faker('zh_CN')

@DebugClass
class Script(QThread):
    sig_data = pyqtSignal(list)
    sig_finish = pyqtSignal(bool)

    def __init__(self, dev: SerialCommunicate, win_idx: int):
        super().__init__()
        self.dev = dev
        self.win_idx = win_idx
        #产品文件
        self.xml = XMLParser()
        # 串口数据缓存区
        self.buffer = BytesBuffer()
        BytesBuffer.set_header(self.xml.default_send_frameheader, self.xml.default_recv_frameheader)
        #帧头 对应 xml  recv项
        self.frameheader_recv_dict = {}
        #记录数据结果
        self.result_list = []
        #
        self.runnig = True

    def stop(self):
        self.runnig = False

    def recv_item_check(self, recvitem, item, frame: bytes):
        checksum = frame[-1]
        data_len = frame[self.xml.frameheader_length]
        frame_data = frame[self.xml.frameheader_length+1: -1]

        if len(frame_data) != data_len:
            raise RuntimeError('recv frame:{}, data:{}, date_len{}'.format(BitArray(frame), BitArray(frame_data), data_len ))

        convert_value = mix.convert_value(frame_data, item)

        #v = "1, 2, 3, 9-15"
        result = mix.value_compare(convert_value, item)

        msg = item.get(XMLParser.AMsg, '')
        tag = item.get(XMLParser.ATag,  '')
        recvitem_tag = recvitem.get(XMLParser.ATag, '')
        funchar = recvitem.get(XMLParser.AFunchar, '')

        value = item.get(XMLParser.AValue, '')
        if msg.count('{') == 2:
            msg = msg.format(expect=value, real=convert_value)
        elif msg.count('{') == 1 and 'expect' in msg:
            msg = msg.format(expect=value)
        elif msg.count('{') == 1 and 'real' in msg:
            msg = msg.format(expect=value)

        tag = '[{}, {}]{}'.format(recvitem_tag, funchar, tag)
        self.result_list.append([tag, msg, result])
        self.sig_data.emit([tag, msg, result])


    def recv_check(self, frame: bytes):
        if frame:
            frameheader = frame[:self.xml.frameheader_length]
            print('frameheader', frameheader, 'frame', frame)
            if frameheader in self.frameheader_recv_dict:
                recv_item = self.frameheader_recv_dict[frameheader]
                for childItem in recv_item.iterchildren():
                    self.recv_item_check(recv_item, childItem, frame)
                mix.send_command(self.dev, self.xml, 'next')
                print('frameheader', frameheader, 'frame', [frame])

    def run(self):
        start_time = datetime.datetime.now()
        self.frameheader_recv_dict = self.xml.frameheader_recv()

        # mix.send_command(self.dev, self.xml, 'stop')
        mix.send_command(self.dev, self.xml, 'connect')
        while self.runnig:
            self.buffer.extend( self.dev.read_available() )
            self.recv_check( self.buffer.currentFrame() )
            # self.msleep(100)

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
        # db.remotedb.create_tables([db.RemoteProductionRecord])
        # db.RemoteProductionRecord.create(msg=msgbuf.getvalue(), result=result, model=Config.PRODUCT_MODEL, version='1.0',
        #                                  start_time=start_time, end_time=end_time, total_time=total_time)

        db.localdb.create_tables([db.LocalProductionRecord])
        db.LocalProductionRecord.create(msg=msgbuf.getvalue(), result=result, model=Config.PRODUCT_MODEL, version='1.0',
                                         start_time=start_time, end_time=end_time, total_time=total_time)

