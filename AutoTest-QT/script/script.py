import os
import io
import random
import datetime
import time
from PyQt5.QtCore import  QThread, pyqtSignal
from faker import Faker
import pandas as pd
from communicate.communicate import SerialCommunicate
from ui.mixin import *
from . import mix
from db import db
from lxml import etree

fake = Faker()

@DebugClass
class Script(QThread):
    sig_finish = pyqtSignal(mix.FinalResult)
    sig_error = pyqtSignal(str)

    sig_item = pyqtSignal(mix.Item)
    sig_item_result = pyqtSignal(mix.ItemResult)
    sig_child_item = pyqtSignal(mix.ChildItem)

    def __init__(self, dev: SerialCommunicate, win_idx: int):
        super().__init__()
        self.dev = dev
        # self.dev.dev.reset_input_buffer()
        # self.dev.dev.reset_output_buffer()
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
        #运行标记
        self.runnig = True
        #存储产品变量
        self.dict = {}
        #总结果
        self.result = True

    def stop(self):
        self.runnig = False
        self.result = False

    def error_frame(self, recvitem, frame: bytes):
        error_msg = ''
        frame_data = frame[self.xml.frameheader_length + 1 + 1: -1]
        for childItem in recvitem.iterchildren():
            convert_value = mix.convert_value(frame_data, childItem)
            result = mix.value_compare(convert_value, childItem)
            if result:
                error_msg += childItem.get(XMLParser.ATag, '') + ','

        self.sig_error.emit(error_msg)
        self.stop()

    def filter_frame(self, recvitem, frame: bytes):
        mix.send_command(self.dev, self.xml, 'filter')

    def general_frame(self, recvitem, frame: bytes):
        recvitem_tag = recvitem.get(XMLParser.ATag, '')
        item = mix.Item(tag=recvitem_tag)
        self.sig_item.emit(item)

        child_results = []
        for childItem in recvitem.iterchildren():
            child_result = self.general_frame_childitem(recvitem, childItem, frame)
            child_results.append(child_result.result)

        result = True
        pass_count = fail_count = total = 0
        total = len(child_results)
        if total:
            pass_count = child_results.count(True)
            fail_count = child_results.count(False)
            if fail_count > 0:
                result = False

        item_result = mix.ItemResult(tag=item.tag, result=result, total=total, pass_count=pass_count, fail_count=fail_count)
        self.sig_item_result.emit(item_result)
        mix.send_command(self.dev, self.xml, 'next')

    def final_frame(self, recvitem, frame: bytes):
        self.runnig = False
        mix.send_command(self.dev, self.xml, 'next')

    def general_frame_childitem(self, recvitem, childitem, frame: bytes) -> mix.ChildItem:
        checksum = frame[-1]
        data_len = frame[self.xml.frameheader_length + 1]
        frame_data = frame[self.xml.frameheader_length + 1 + 1: -1]

        convert_value = mix.convert_value(frame_data, childitem)

        #v = "1, 2, 3, 9-15"
        result = mix.value_compare(convert_value, childitem)

        msg = childitem.get(XMLParser.AMsg, '')
        tag = childitem.get(XMLParser.ATag,  '')
        recvitem_tag = recvitem.get(XMLParser.ATag, '')
        funchar = recvitem.get(XMLParser.AFunchar, '')
        store_value = childitem.get(XMLParser.AStore, '')
        if store_value:
            self.dict[store_value] = convert_value

        value = childitem.get(XMLParser.AValue, '')
        if msg.count('{') == 2:
            msg = msg.format(expect=value, real=convert_value)
        elif msg.count('{') == 1 and 'expect' in msg:
            msg = msg.format(expect=value)
        elif msg.count('{') == 1 and 'real' in msg:
            msg = msg.format(real=convert_value)

        child_item_result = mix.ChildItem(ptag=recvitem_tag, tag=tag, msg=msg, result=result)
        self.result_list.append(child_item_result)
        self.sig_child_item.emit(child_item_result)
        return child_item_result

    def recv_check(self, frame: bytes):
        if frame:
            frameheader_funchar = frame[:self.xml.frameheader_length + 1]
            if frameheader_funchar in self.frameheader_recv_dict:
                recv_item = self.frameheader_recv_dict[frameheader_funchar]
                recv_item_flag = recv_item.get(XMLParser.AFlag, 'general')

                if 'general' in recv_item_flag :
                    self.general_frame(recv_item, frame)
                elif 'filter' in recv_item_flag:
                    self.filter_frame(recv_item, frame)
                elif 'final' in recv_item_flag:
                    self.final_frame(recv_item, frame)
                elif 'error' in recv_item_flag:
                    self.error_frame(recv_item, frame)

    def connect_test(self):
        mix.send_command(self.dev, self.xml, 'connect')
        self.msleep(500)
        mix.send_command(self.dev, self.xml, 'test')

    def run(self):
        start_time = datetime.datetime.now()
        self.frameheader_recv_dict = self.xml.frameheader_recv()
        self.connect_test()
        while self.runnig:
            self.buffer.extend( self.dev.read_available() )
            self.recv_check( self.buffer.currentFrame() )

        result_item_list = []
        for result_item in self.result_list:
            result_item_list.append(result_item[2])
        result = False if False in result_item_list else True
        result = result and self.result
        end_time = datetime.datetime.now()
        finalResult = mix.FinalResult(result=result, total_time=(end_time - start_time).seconds)
        self.sig_finish.emit(finalResult)
        self.storeTestResult(result, start_time, end_time)

    def storeTestResult(self, result, start_time, end_time):
        if len(self.result_list) == 0: return None
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
                                         start_time=start_time, end_time=end_time, total_time=total_time, chipid=self.dict.get('@CHIPID', ''))


