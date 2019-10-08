import serial
from enum import Enum, auto
from PyQt5.QtCore import QObject, pyqtSignal

#设备状态
class DevStatus(Enum):
    closed = auto() #关闭
    opened = auto() #活动
    exception = auto() #异常

class SerialCommunicate(QObject):
    writeSig = pyqtSignal(bytes)
    readSig = pyqtSignal(bytes)
    def __init__(self, **kwargs):
        """
        :param kwargs:
        串口参数，可用key为 ['parity', 'baudrate', 'bytesize', 'xonxoff', 'rtscts', 'timeout', 'inter_byte_timeout',
         'stopbits', 'dsrdtr', 'write_timeout'] + 'name'
        """
        super().__init__()
        self.dev = serial.Serial()
        self.dev.port = kwargs.get('name')
        self.settings = kwargs
        self.status = DevStatus.closed
        self.apply_settings(**self.settings)

    def apply_settings(self, **kwargs):
        try:
            for k, v in kwargs.items():
                if isinstance(v, str) and v.isdigit():
                    kwargs[k] = int(v)

            self.dev.port = kwargs.get('name', '')
            self.settings.update(kwargs)
            self.dev.apply_settings(self.settings)
        except Exception as e:
            self.status = DevStatus.exception

    def get_settings(self):
        tmp_setings = dict(self.settings)
        for k, v in self.settings.items():
            if isinstance(v, int):
                tmp_setings[k] = str(v)

        return tmp_setings

    def connect(self):
        try:
            if self.status in [DevStatus.closed, DevStatus.exception]:
                self.dev.open()
        except Exception as e:
            self.status = DevStatus.exception
        else:
            self.status = DevStatus.opened

    def read_line(self, fix:bool=False):
        data = self.dev.readline()
        self.readSig.emit(data)
        return data

    def read_until(self, match:bytes, size:int, fix:bool=False):
        data = self.dev.read_until(terminator=match, size=size)
        self.readSig.emit(data)
        return data

    def read_available(self, fix:bool=False):
        if self.dev.in_waiting:
            data = self.dev.read(self.dev.in_waiting)
        else:
            data = b''
        self.readSig.emit(data)
        return data

    def write(self, data:bytes):
        self.writeSig.emit(data)
        return self.dev.write(data)

    def write_line(self, data:bytes, linefeed:bytes=b'\n'):
        self.writeSig.emit(data+linefeed)
        return self.dev.write(data+linefeed)

    @property
    def type(self):
        return 'serial'

    @property
    def name(self):
        return self.dev.name

    def set_read_timeout(self, timeout:float):
        if self.status == DevStatus.opened:
            self.dev.timeout = float(timeout)

    def close(self):
        self.dev.close()
        self.status = DevStatus.closed

    def flush(self):
        self.dev.reset_input_buffer()
        self.dev.reset_output_buffer()

    def __repr__(self):
        return '<name={} baudrate={} status={}>'.format(self.dev.name, self.dev.baudrate, self.status.name)
