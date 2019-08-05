import re
import arrow
from lxml import etree
from bitstring import BitArray
from config.config import Config
from functools import wraps, partial
import inspect
import traceback
import logging
from pubsub import pub

class XMLParser:
    AHeader  = 'header'
    AFunchar = 'funchar'
    Abytepos = 'bytepos'
    Abitpos = 'bitpos'
    AValue = 'value'
    AConvert = 'convert'

    def __init__(self):
        if Config.PRODUCT_XML_CHANGED:
            Config.PRODUCT_XML_CHANGED = False
            self.tree = etree.parse(Config.PRODUCT_XML)
            Config.PRODUCT_XML_TREE = self.tree
        else:
            self.tree = Config.PRODUCT_XML_TREE

        self.root = self.tree.getroot()
        self.frameheader_length = 3

        self._recv_path = './recv'
        self._send_path = './send'

    def iter_recv(self):
        return self.root.iterfind(self._recv_path)

    def iter_send(self):
        return self.root.iterfind(self._send_path)

    def frameheader_recv(self):
        frameheader_recv_dict = {}
        for recv_item in self.iter_recv():
            header = BitArray('{},{}'.format(recv_item.get(self.AHeader), recv_item.get(self.AFunchar)))
            frameheader_recv_dict[header.bytes] = recv_item

        return frameheader_recv_dict

class BytesBuffer:
    def __init__(self, header_sign:bytes):
        self.header_sign = header_sign
        self.buffer = bytearray()
        self.frame_list = []

    def extend(self, data:bytes):
        self.buffer.extend(data)

    @property
    def firstFrame(self):
        if len(self.frame_list):
            return self.frame_list[0]
        else:
            return b''

    @property
    def lastFrame(self):
        if len(self.frame_list):
            return self.frame_list[-1]
        else:
            return b''

    @property
    def currentFrame(self):
        pattern = b'%b.+?(?=%b)' % (self.header_sign, self.header_sign)
        match = re.search(pattern, self.buffer)
        if match:
            frame = match.group()
            self.buffer = self.buffer.replace(frame, b'')
            self.frame_list.append(frame)
            return frame
        return b''

    @property
    def frames(self):
        return self.frame_list

def convert(type_, bytedata:BitArray):
    if type_ == 'int':
        return str(bytedata.int)
    else:
        return bytedata

def parse_datetime(value):
    a = arrow.get(value)
    return a.format('YYYY-MM-DD HH:mm:ss')

class DebugClass:
    def __init__(self, cls, debug=True):
        self.debug = debug
        wraps(cls)(self)
        for funname, fun in inspect.getmembers(cls):
            if not funname.startswith('__') and inspect.isfunction(fun):
                fun = self.debugfun(fun)
                setattr(cls, funname, fun)

    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)

    def debugfun(self, func=None, *, level=logging.ERROR):
        if func is None:
            return partial(self.debugfun, level=level)

        @wraps(func)
        def wrapper(*args, **kwargs):
            value = None
            if self.debug:
                try:
                    value = func(*args, **kwargs)
                except Exception as e:
                    print(traceback.format_exc())
                    pub.sendMessage(Config.TOPIC_EXCEPTION,  triggered=True)
                    Config.LOGGER.log(level, traceback.format_exc())
            else:
                value = func(*args, **kwargs)

            return value

        return wrapper
