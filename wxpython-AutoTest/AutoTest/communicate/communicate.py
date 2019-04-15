#coding:utf-8
import six, abc
import ftfy
import serial
from telnetlib import Telnet

#抽象通信基类
@six.add_metaclass(metaclass=abc.ABCMeta)
class CommunicateBase(object):
    #连接
    @abc.abstractmethod
    def connect(self):pass

    #读取一行
    @abc.abstractmethod
    def read_line(self, timeout, **kwargs):pass

    #读取通信设备可用的数据
    @abc.abstractmethod
    def read_available(self, timeout, **kwargs):pass

    #读取到匹配的内容
    @abc.abstractmethod
    def read_until(self, match, **kwargs):pass

    #写数据
    @abc.abstractmethod
    def write(self, data, **kwargs):pass

    #写一行数据
    @abc.abstractmethod
    def write_line(self, data, linefeed, **kwargs):pass

    #通信类型
    @abc.abstractmethod
    def type(self):pass

    @abc.abstractmethod
    def close(self):pass

    @abc.abstractmethod
    def alive(self):pass

    @abc.abstractmethod
    def apply_settings(self, **kwargs):pass

    @abc.abstractmethod
    def set_read_timeout(self, timeout):pass

    # 对数据进行修复
    def _fix_data(self, data, fix=True):
        if fix:
            return ftfy.fix_text(unicode(data, errors='ignore'))
        return data


class SerialCommunicate(CommunicateBase):
    def __init__(self, **kwargs):
        """
        :param kwargs:
        串口参数，可用key为 ['parity', 'baudrate', 'bytesize', 'xonxoff', 'rtscts', 'timeout', 'inter_byte_timeout',
         'stopbits', 'dsrdtr', 'write_timeout'] + 'port'
        """
        self.dev = serial.Serial()
        self.dev.port = kwargs.get('name')
        self.settings = kwargs
        self.apply_settings(**self.settings)

    def apply_settings(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, str) and v.isdigit():
                kwargs[k] = int(v)
        self.settings.update(kwargs)
        self.dev.apply_settings(self.settings)

    def connect(self):
        self.dev.open()

    def read_line(self, timeout=None, **kwargs):
        """
        :param timeout:  超时
        :param kwargs:  fix=修复数据
        :return:
        """
        if timeout:
            self.dev.timeout = timeout

        data = self.dev.readline()
        return self._fix_data(data, kwargs.get('fix', False))

    def read_until(self, match, **kwargs):
        """
           :param timeout:  超时
           :param kwargs:  fix=修复数据
           :return:
        """
        timeout, size = kwargs.get('timeout'), kwargs.get('size')
        if timeout:
            self.dev.timeout = timeout

        data = self.dev.read_until(terminator=match, size=size)
        return self._fix_data(data, fix=kwargs.get('fix', False))

    def read_available(self, timeout=None, **kwargs):
        """
           :param timeout:  超时
           :param kwargs:  fix=修复数据
           :return:
        """
        if self.dev.in_waiting:
            data = self.dev.read(self.dev.in_waiting)
        else:
            data = ''

        return self._fix_data(data, fix=kwargs.get('fix', False))

    def write(self, data, **kwargs):
        """
           :param kwargs:  write_timeout=写超时
           :return:
        """
        write_timeout = kwargs.get('write_timeout')
        if write_timeout:
            self.dev.write_timeout = write_timeout

        return self.dev.write(data)

    def write_line(self, data, linefeed='\n', **kwargs):
        """
        :param data:
        :param linefeed:  换行符
        :param kwargs:  write_timeout=写超时
        :return:
        """
        write_timeout = kwargs.get('write_timeout')
        if write_timeout:
            self.dev.write_timeout = write_timeout

        return self.dev.write(data+linefeed)

    @property
    def type(self):
        return 'serial'

    def set_read_timeout(self, timeout):
        if self.alive():
            self.dev.timeout = float(timeout)

    def close(self):
        self.dev.close()

    def alive(self):
        return self.dev.isOpen()

    #private
    def _active(self):
        try:
            _ = self.dev.inWaiting()
        except Exception :
            return False
        return True

    def __str__(self):
        return '{!s}'.format(self.dev)

class TelnetCommnuicate(CommunicateBase):
    def __init__(self, **kwargs):
        """
         :param kwargs: 可用参数['host', 'port', 'timeout]
         """
        self.dev = Telnet()
        self.settings = kwargs

    def apply_settings(self, **kwargs):
        self.settings = kwargs

    def connect(self):
        if self.alive():
            self.close()
        host, port, timeout = self.settings.get('ip'), self.settings.get('port'), self.settings.get('timeout', 3)
        self.dev.open(host, int(port), int(timeout))

    def read_until(self, match, **kwargs):
        timeout = kwargs.get('timeout', 1)
        data = self.dev.read_until(match=match, timeout=timeout)
        return self._fix_data(data, fix=kwargs.get('fix', False))

    def read_line(self, timeout=1, **kwargs):
        data = self.read_until(match='\n', timeout=timeout, **kwargs)
        return self._fix_data(data, fix=kwargs.get('fix', False))

    def read_available(self, timeout=None, **kwargs):
        data = ''
        try:
            data =  self.dev.read_very_eager()
        except Exception:
            pass
        return self._fix_data(data, fix=kwargs.get('fix', False))

    def write(self, data, **kwargs):
        self.dev.write(data)

    def write_line(self, data, linefeed='\r\n', **kwargs):
        self.dev.write(data+linefeed)

    @property
    def type(self):
        return 'telnet'

    def set_read_timeout(self, timeout):
        if self.alive():
            self.dev.timeout = float(timeout)

    def close(self):
        if self.alive():
            self.dev.close()

    def alive(self):
        try:
            alive = self.dev.fileno()
            self.dev.sock_avail()
        except Exception as e:
            alive = False
        return alive

    def __str__(self):
        return '{!s}'.format(self.dev)

#通信类工厂函数
def communicate_factory(type, **kwargs):
    instance = None
    if type == 'serial':
        instance = SerialCommunicate(**kwargs)
    elif type == 'telnet':
        instance = TelnetCommnuicate(**kwargs)

    return instance

