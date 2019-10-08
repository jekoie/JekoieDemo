import io
import random
import os
import datetime
import time
from PyQt5.QtCore import  QThread, QRunnable ,pyqtSignal
from faker import Faker
import pandas as pd
from communicate.communicate import SerialCommunicate
from ui.mixin import *
from script import mix
from db import db
from lxml import etree

class OffAlarm(QRunnable):
    def __init__(self, win_idx):
        super().__init__()
        self.dev =  Config.RC[win_idx]['dev'] #type:SerialCommunicate
        self.xml = XMLParser()
        self.buffer = BytesBuffer()
        self.dev.flush()

    def run(self):
        mix.send_command(self.dev, self.xml, 'error')

class StepIn(QRunnable):
    def __init__(self, win_idx):
        super().__init__()
        self.dev =  Config.RC[win_idx]['dev'] #type:SerialCommunicate
        self.xml = XMLParser()
        self.buffer = BytesBuffer()
        BytesBuffer.set_header(self.xml.default_send_frameheader, self.xml.default_recv_frameheader)
        self.dev.flush()

    def run(self):
        mix.send_command(self.dev, self.xml, 'connect')
        while True:
            self.buffer.extend(self.dev.read_available())
            frame = self.buffer.currentFrame()
            if frame:
                mix.send_command(self.dev, self.xml, 'next')
                break

        time.sleep(1)
        mix.send_command(self.dev, self.xml, 'stepin')

class StepOut(QRunnable):
    def __init__(self, win_idx):
        super().__init__()
        self.dev =  Config.RC[win_idx]['dev']
        self.xml = XMLParser()
        self.buffer = BytesBuffer()
        BytesBuffer.set_header(self.xml.default_send_frameheader, self.xml.default_recv_frameheader)

    def run(self):
        mix.send_command(self.dev, self.xml, 'stepout')

class Step(QThread):
    sig_item_result = pyqtSignal(mix.ItemResult)
    sig_child_item = pyqtSignal(mix.ChildItem)
    sig_finish = pyqtSignal(float)
    def __init__(self, win_idx,  item_tag):
        super().__init__()
        self.runing = True

        self.dev = Config.RC[win_idx]['dev']
        self.xml = XMLParser()
        self.buffer = BytesBuffer()
        BytesBuffer.set_header(self.xml.default_send_frameheader, self.xml.default_recv_frameheader)
        self.item_tag = item_tag
        self.item = self.xml.root.find('./recv[@tag="{}"]'.format(self.item_tag) )
        self.funchar = self.item.get(XMLParser.AFunchar, '')

    def stop(self):
        self.runing = False

    def item_check(self, frame:bytes):
        if frame and frame[2] == int(self.funchar, 16):
            child_results = []
            for childItem in self.item.iterchildren():
                child_result = self.general_frame_childitem(childItem, frame)
                child_results.append(child_result.result)

            result = True
            pass_count = fail_count = total = 0
            total = len(child_results)
            if total:
                pass_count = child_results.count(True)
                fail_count = child_results.count(False)
                if fail_count > 0:
                    result = False

            flag = self.item.get(XMLParser.AFlag, 'general')
            item_result = mix.ItemResult(tag=self.item_tag, flag=flag, funchar=self.funchar, result=result, total=total, pass_count=pass_count, fail_count=fail_count)
            self.sig_item_result.emit(item_result)
            self.runing = False

    def general_frame_childitem(self, childitem, frame: bytes) -> mix.ChildItem:
        checksum = frame[-1]
        data_len = frame[self.xml.frameheader_length + 1]
        frame_data = frame[self.xml.frameheader_length + 1 + 1: -1]

        convert_value = mix.convert_value(frame_data, childitem)

        #v = "1, 2, 3, 9-15"
        result = mix.value_compare(convert_value, childitem)

        msg = childitem.get(XMLParser.AMsg, '')
        tag = childitem.get(XMLParser.ATag,  '')

        value = childitem.get(XMLParser.AValue, '')
        if msg.count('{') == 2:
            msg = msg.format(expect=value, real=convert_value)
        elif msg.count('{') == 1 and 'expect' in msg:
            msg = msg.format(expect=value)
        elif msg.count('{') == 1 and 'real' in msg:
            msg = msg.format(real=convert_value)

        child_item_result = mix.ChildItem(ptag=self.item_tag, tag=tag, msg=msg, result=result)
        self.sig_child_item.emit(child_item_result)
        return child_item_result

    def recv_check(self,  frame: bytes):
        if frame:
            frameheader_funchar = frame[:self.xml.frameheader_length + 1]
            if frameheader_funchar in self.frameheader_recv_dict:
                self.item_check(frame)
                mix.send_command(self.dev, self.xml, 'next')

    def run(self):
        start_time = datetime.datetime.now()
        self.frameheader_recv_dict = self.xml.frameheader_recv()
        mix.send_command(self.dev, self.xml, 'step', self.funchar)
        while self.runing:
            self.buffer.extend(self.dev.read_available())
            self.recv_check(self.buffer.currentFrame())
        end_time = datetime.datetime.now()
        self.sig_finish.emit( (end_time - start_time).total_seconds() )





