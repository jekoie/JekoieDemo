#coding:utf-8
import wx
import wx.lib
import re
import time
import sys
import traceback
import binascii
import serial
import pandas as pd
import wx.lib.pubsub.pub as pub
import wx.lib.newevent
import copy
from lxml import etree
from datetime import datetime
from config.config import Config, DeviceState
from ui import tool
from instrument import instrument

PASS, FAIL, ERROR = 'PASS', 'FAIL', 'ERROR'
#通知主线程弹出对话框
(ThreadDialogEvent, EVT_THREAD_DIALOG) = wx.lib.newevent.NewEvent()
#线程结束时通知主线程
(ThreadDeathEvent, EVT_THREAD_DEATH) = wx.lib.newevent.NewEvent()

class Product(object):
    def __init__(self, product_dict, thread_queue , win):
        try:
            #运行状态
            self._keepgoing = True
            # 产品字典
            self.dict = product_dict
            #产品配置文件
            self.xml = None
            #自动过站
            self.pass_station = False
            #显示mac地址
            self.show_mac = True
            #产品名称
            self.product_name = None
            #SN -- MAC 对应组装绑定信息
            self.bind_info = None
            #MES相关字典
            self.mes_attr = copy.deepcopy(Config.mes_attr)
            # 设备窗口
            self.devwin = win
            self.dev1_sn = self.devwin.dev1_sn
            #状态 label
            self.status_text = self.devwin.status_text
            #页窗口
            self.pagewin1, self.pagewin2 = Config.windows[self.devwin]
            #数据队列
            self.queue = thread_queue
            #对应设备窗口编号
            self.win_idx = self.devwin.win_idx
            #窗体正在使用中
            Config.popup[self.win_idx].update({'used':True})
            #区域
            self.section1 =  self.pagewin1.section_area
            self.section2 =  self.pagewin2.section_area if self.pagewin2 else None
            # 运行日志
            self.log1 = self.pagewin1.log_area
            self.log2 = self.pagewin2.log_area if self.pagewin2 else None
            #信尔泰记录
            self.telelog = ''
            #设备
            self.dev1, _ = Config.getdevice(self.pagewin1.win_idx)
            self.dev2, _ = Config.getdevice(self.pagewin2.win_idx) if self.pagewin2 else (None, None)
            Config.update_device_status(self.pagewin1.win_idx, DeviceState.background)
            if self.pagewin2:
                Config.update_device_status(self.pagewin2.win_idx, DeviceState.background)
        except Exception as e:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    #停止线程
    def stop(self):
        self._keepgoing = False

    def close(self, start_time, end_time, diff_time, result):
        self.record_message(start_time, end_time, diff_time, result)
        if Config.mode['mode'] == 'double' and 'B_SN' in self.dict:
            self.record_message(start_time, end_time, diff_time, result, from_='slave')

        if self.pass_station:
            self.mes_write(result)
            pub.sendMessage(Config.topic_notify_mesarea, status=True)

    def postclose(self, result, abnormaled=False):
        if result == PASS:
            self.status_text.SetLabel(PASS)
            self.devwin.SetBackgroundColour(Config.colour_green)
            Config.popup[self.win_idx].update({'byhand': True})
        elif result == FAIL and not abnormaled:
            self.status_text.SetLabel(FAIL)
            self.devwin.SetBackgroundColour(Config.colour_red)
            Config.popup[self.win_idx].update({'byhand': False})
            Config.worktable_changed = True
        elif result == FAIL and abnormaled:
            self.status_text.SetLabel(ERROR)
            self.devwin.SetBackgroundColour(Config.colour_gray)
            Config.popup[self.win_idx].update({'byhand': False})
            Config.worktable_changed = True

        self.devwin.Refresh()
        Config.vars = self.dict
        Config.popup[self.win_idx].update({'used': False})
        Config.update_device_status(self.pagewin1.win_idx, DeviceState.foreground)
        if self.pagewin2:
            Config.update_device_status(self.pagewin2.win_idx, DeviceState.foreground)

    #获取节点值
    def get_tag_value(self, tag, attr, default=''):
        attr_value =  tag.get(attr, default)
        flag_value = tag.get('flag', '')
        if 'skip' in flag_value: return  attr_value
        if attr_value == None: return  None
        if '@' in attr_value:
            for key in  sorted( re.findall('(@\w+)', attr_value), key=len,  reverse=True ):
                value = self.dict[key]
                attr_value = attr_value.replace(key, str(value) )

        if '$' in attr_value:
            for key in sorted(re.findall(r'(\$\w+)', attr_value), key=len, reverse=True):
                value = self.dict[key]
                attr_value = attr_value.replace(key, str(value))
        return attr_value

    def enter_normal_mode(self, item=None):
        info = ''
        istimeout = False
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        cmd_to = self.get_tag_value(item, 'to', 'master')
        _dev, _options = (self.dev1, self.options) if cmd_to == 'master' else (self.dev2, self.options2)

        _username = item.get('username', self.get_tag_value(_options, 'username') )
        _passwd = item.get('password', self.get_tag_value(_options, 'password') )

        _hostword = self.get_tag_value(_options, 'hostword', 'raisecom')
        _debugcmd = self.get_tag_value(_options, 'debug_cmd')
        _supercmd = self.get_tag_value(_options, 'super_cmd')
        _configcmd = self.get_tag_value(_options, 'config_cmd')
        _linefeed = self.get_tag_value(_options, 'linefeed', '\n')
        _exitcmd = self.get_tag_value(_options, 'exit_cmd', 'quit')

        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(_dev, _linefeed)
        _dev.set_read_timeout(1)
        start_time = time.time()
        while True:
            line = _dev.read_line(fix=True)
            line = self.log_message(line, cmd_to)
            info += line

            if not self._keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match(r'^(login|username):', line, re.I):
                if re.match(r'^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(_dev, _username + _linefeed)
            elif re.match(r'password:', line, re.I):
                if re.match(r'password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    self.write_cmd(_dev, _username + _linefeed)
            elif re.match(r'{}>'.format(_hostword), line, re.I):
                break
            elif re.match(r'{}[^\r\n]+'.format(_hostword), line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif re.match('->', line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(_dev, _linefeed)
                else:
                    continue
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return info, istimeout

    def enter_super_mode(self, item=None):
        info = ''
        istimeout = False
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        cmd_to = self.get_tag_value(item, 'to', 'master')
        _dev, _options = (self.dev1, self.options) if cmd_to == 'master' else (self.dev2, self.options2)

        _hostword = self.get_tag_value(_options, 'hostword', 'raisecom')
        _username = item.get('username', self.get_tag_value(_options, 'username'))
        _passwd = item.get('password', self.get_tag_value(_options, 'password'))
        _debugcmd = self.get_tag_value(_options, 'debug_cmd')
        _supercmd = self.get_tag_value(_options, 'super_cmd')
        _configcmd = self.get_tag_value(_options, 'config_cmd')
        _linefeed = self.get_tag_value(_options, 'linefeed', '\n')
        _exitcmd = self.get_tag_value(_options, 'exit_cmd', 'quit')

        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(_dev, _linefeed)
        _dev.set_read_timeout(1)
        start_time = time.time()

        while True:
            line = _dev.read_line(fix=True)
            line = self.log_message(line, cmd_to)
            info += line
            if not self._keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('{}>'.format(_hostword), line, re.I):
                if re.match('{}>\s*{}[\r\n]+'.format(_hostword, _supercmd), line, re.I):
                    self.write_cmd(_dev, _passwd + _linefeed)
                else:
                    self.write_cmd(_dev, _supercmd + _linefeed)
            elif re.match('{}#'.format(_hostword), line, re.I):
                if re.match('{}#\s*{}[\r\n]+'.format(_hostword, _exitcmd), line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    break
            elif re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(_dev, _username + _linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    self.write_cmd(_dev, _passwd + _linefeed)
            elif re.match('{}[^\r\n]+'.format(_hostword), line, re.I):
                if re.match('{}.+exit|quit'.format(_hostword), line, re.I):
                    continue
                else:
                    self.write_cmd(_dev, _exitcmd + _linefeed)
            elif re.match('->', line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(_dev, _linefeed)
                else:
                    continue

        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return info, istimeout

    def enter_debug_mode(self, item=None):
        info = ''
        istimeout = False
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        cmd_to = self.get_tag_value(item, 'to', 'master')
        _dev, _options = (self.dev1, self.options) if cmd_to == 'master' else (self.dev2, self.options2)

        _hostword = self.get_tag_value(_options, 'hostword', 'raisecom')
        _username = item.get('username', self.get_tag_value(_options, 'username'))
        _passwd = item.get('password', self.get_tag_value(_options, 'password'))
        _debugcmd = self.get_tag_value(_options, 'debug_cmd')
        _supercmd = self.get_tag_value(_options, 'super_cmd')
        _configcmd = self.get_tag_value(_options, 'config_cmd')
        _linefeed = self.get_tag_value(_options, 'linefeed', '\n')
        _exitcmd = self.get_tag_value(_options, 'exit_cmd', 'quit')

        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(_dev, _linefeed)
        _dev.set_read_timeout(1)
        start_time = time.time()

        while True:
            line = _dev.read_line( fix=True)
            line = self.log_message(line, cmd_to)
            info += line

            if not self._keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('{}>'.format(_hostword), line, re.I):
                if re.match('{}>\s*{}[\r\n]+'.format(_hostword, _supercmd), line, re.I):
                    self.write_cmd(_dev, _passwd + _linefeed)
                else:
                    self.write_cmd(_dev, _supercmd + _linefeed)
            elif re.match('{}\(debug\)#'.format(_hostword), line, re.I):
                if re.match('{}\(debug\)#\s*{}[\r\n]+'.format(_hostword, _exitcmd), line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    break
            elif re.match('{}#'.format(_hostword), line, re.I):
                if  re.match('{}#\s*{}[\r\n]+'.format(_hostword, _debugcmd), line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    self.write_cmd(_dev, _debugcmd + _linefeed)
            elif re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(_dev, _username + _linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    self.write_cmd(_dev, _passwd + _linefeed)
            elif re.match('{}[^\r\n]+'.format(_hostword), line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif re.match('->', line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(_dev, _linefeed)
                else:
                    continue
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return  info, istimeout

    def enter_config_mode(self, item=None):
        info = ''
        istimeout = False
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        cmd_to = self.get_tag_value(item, 'to', 'master')
        _dev, _options = (self.dev1, self.options) if cmd_to == 'master' else (self.dev2, self.options2)

        _hostword = self.get_tag_value(_options, 'hostword', 'raisecom')
        _username = item.get('username', self.get_tag_value(_options, 'username'))
        _passwd = item.get('password', self.get_tag_value(_options, 'password'))
        _debugcmd = self.get_tag_value(_options, 'debug_cmd')
        _supercmd = self.get_tag_value(_options, 'super_cmd')
        _configcmd = self.get_tag_value(_options, 'config_cmd')
        _linefeed = self.get_tag_value(_options, 'linefeed', '\n')
        _exitcmd = self.get_tag_value(_options, 'exit_cmd', 'quit')

        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(_dev, _linefeed)
        _dev.set_read_timeout(1)
        start_time = time.time()
        while True:
            line = _dev.read_line(fix=True)
            line = self.log_message(line, cmd_to)
            info += line

            if not self._keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('{}>'.format(_hostword), line, re.I):
                if re.match('{}>\s*{}[\r\n]+'.format(_hostword, _supercmd), line, re.I ):
                    self.write_cmd(_dev, _passwd + _linefeed)
                else:
                    self.write_cmd(_dev, _supercmd + _linefeed)
            elif re.match('{}\(config\)#'.format(_hostword), line, re.I):
                if re.match('{}\(config\)#\s*{}[\r\n]+'.format(_hostword, _exitcmd), line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    break
            elif re.match('{}#'.format(_hostword), line, re.I):
                if  re.match('{}#\s*{}[\r\n]+'.format(_hostword, _configcmd), line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    self.write_cmd(_dev, _configcmd + _linefeed)
            elif re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(_dev, _username + _linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(_dev, _linefeed)
                else:
                    self.write_cmd(_dev, _passwd + _linefeed)
            elif re.match('{}[^\r\n]+'.format(_hostword), line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif re.match('->', line, re.I):
                self.write_cmd(_dev, _exitcmd + _linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(_dev, _linefeed)
                else:
                    continue

            if time.time() - start_time > timeout and self._keepgoing:
                istimeout = True
                break
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return info, istimeout

    def log_message(self, line, which):
        line = re.sub(r'[\n]{1,}', '\n', line)
        _log = self.log1 if which == 'master' else self.log2
        try:
            wx.CallAfter(_log.AppendText, line)
            self.recored_process(content=line, type="echo")
        except Exception:
            Config.logger.error(traceback.format_exc())
            self.section_message('软件检测到错误，请重新启动', which, True)
        return line

    # data = ('stage', 'result', 'start_time', 'end_time'， 'diff_time')
    def section_message(self, data, which='both', showcolor=False):
        def write_section(section, message):
            if section:
                wx.CallAfter(section.AppendText, message + '\n')

            if showcolor:
                text_attr = wx.TextAttr(wx.Colour(255, 0, 0), wx.Colour(255, 255, 255))
                if section:
                    pos_list = tool.find_pos(message, section.GetValue(), section.GetValue())
                    for start_pos, end_pos in pos_list:
                        wx.CallAfter(section.SetStyle, start_pos, end_pos, text_attr)

        message = ''
        if which == 'master':
            section = (self.section1, None)
        elif which == 'slave':
            section = (None, self.section2)
        else:
            section = (self.section1, self.section2)

        if isinstance(data, tuple):
            message = u'{:30s}\t{}\t{}\t{}\t{}s'.format(*data)
            if data[1] == FAIL: showcolor=True
        elif isinstance(data, basestring):
            message = data

        write_section(section[0], message)
        write_section(section[1], message)

    def recored_process(self, content=None, type="unset"):
        if type == 'mode_in':
            Config.processhandler.write(u'进入 {} 步骤\n'.format(content))
        elif type == "mode_out":
            Config.processhandler.write(u'离开 {} 步骤\n'.format(content))
        elif type == "cmd":
            Config.processhandler.write(u'发送命令:{}\t命令属性{}\n'.format([content[0] ], content[1]) )
        elif type == "echo":
            if content:
                Config.processhandler.write(u'回显内容:{}\n'.format([content]))
        elif type == "unset":
            Config.processhandler.write(u'type unset:{}\n'.format([content]))

    def write_cmd(self, dev, cmd='', extra={} ):
        dev.write(cmd)
        self.recored_process(content=(cmd, extra), type="cmd")

    #sn对应的MAC是否使用
    def mac_used(self, sn_value ,mac_value):
        #rel_item 形式('103002027500S17C28S0001D', 'C8:50:E9:6E:40:74', 'C8:50:E9:6E:40:75', '000E5E-001730S17C27S0010')
        if Config.worktable_loaded:
            if self.bind_info is not None:
                if mac_value == self.bind_info[1]:
                    return True
                else:
                    tip_msg = u'扫入：{}\n组装绑定记录为：{}'.format(mac_value, self.bind_info[1])
                    msg_value = self.get_message_value(tip_msg,  u'{}：{}警告'.format(self.pagewin1.GetName(), sn_value),
                        style=wx.OK | wx.CANCEL | wx.ICON_WARNING, data={'okcancel': (u'继续测试', u'取消测试')})
                    return msg_value
            else:
                tip_msg = u'组装SN:{}\nMAC:{}无绑定关系'.format(sn_value, mac_value)
                msg_value = self.get_message_value(tip_msg, u'{}：{}警告'.format(self.pagewin1.GetName(), sn_value),
                        style=wx.OK | wx.CANCEL | wx.ICON_WARNING, data={'okcancel': (u'继续测试', u'取消测试')})
                return msg_value

        return True

    #选择工序
    def choose_workstage(self):
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='WORKSTAGE', data={'win': self.pagewin1, 'xml': self.xml})
        wx.PostEvent(self.devwin, evt)
        status, workstage_value = self.queue.get()
        return status, workstage_value

    #获取MAC
    def get_mac(self):
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='MAC', data={'win': self.pagewin1})
        wx.PostEvent(self.devwin, evt)
        status, mac_value = self.queue.get()
        return status, mac_value

    #获取SN
    def get_sn(self):
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='SN', data={'win': self.pagewin1})
        wx.PostEvent(self.devwin, evt)
        status, sn_value = self.queue.get()
        return status, sn_value

    #获取消息框判断值
    def get_message_value(self, msg, caption, style, data = {}):
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='MESSAGE', msg=msg, caption=caption, style=style, data=data, win=self.pagewin1)
        wx.PostEvent(self.devwin, evt)
        message_value = self.queue.get()
        return message_value

    #获取自定义值
    def get_self_define_value(self, item):
        win = self.pagewin1 if item.get('to', 'master') == 'master' else self.pagewin2
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='WORKSTAGE_MSGBOX', data={'win':win, 'item': item})
        wx.PostEvent(self.devwin, evt)
        status, workstage_msgbox_value = self.queue.get()
        return status, workstage_msgbox_value

    #工序弹框
    def workstage_msgbox(self, station_id='', sn_value=''):
        node = self.xml.root.find("./workstage/*[@value='{}']".format(station_id))
        if node is None: return True
        self.pass_station = True if node.get('pass_station', 'False') == 'True' else False
        self.show_mac = True if node.get('show_mac', 'True') == 'True' else False

        if Config.mode['repaire_mode']: self.pass_station = False
        #弹出MAC框
        if self.show_mac:
            status, mac_value = self.get_mac()
            if not status: return False
            if not self.mac_used(sn_value, mac_value): return False
        else:
            mac_value = "00:00:00:00:00:00"

        self.dict.update({'@MAC': mac_value})
        self.dict.update(tool.macAddrCreator(mac_value))

        #弹出自定义框
        for item in node.getchildren():
            status, workstage_msgbox_value = self.get_self_define_value(item)
            if status:
                if 'mac' in item.get('flag', ''):
                    self.dict['B_MAC'] = workstage_msgbox_value.values()[0]
                elif 'sn' in item.get('flag', ''):
                    self.dict['B_SN'] = workstage_msgbox_value.values()[0]

                self.dict.update(workstage_msgbox_value)
            else:
                return False
        return True

    def prepare(self):
        status, sn_value = self.get_sn()
        if not status: return False

        if Config.mode['workorder_mode'] and Config.worktable_changed:  #工单模式，工单号只加载一次
            Config.worktable_changed = False
            Config.product_xml = tool.getProductXML(Config.ftpbase_anonymous, self.mes_attr.get('workjob_review', 'default'), sn_value)
        else:   #非工单模式，工单号每次都加载
            Config.product_xml = tool.getProductXML(Config.ftpbase_anonymous, self.mes_attr.get('workjob_review', 'default'), sn_value)

        self.xml, self.product_name = Config.product_xml
        if self.xml is None:
            Config.worktable_changed = True
            self.section_message('在 ftp://192.168.60.70/AutoTest-Config/config.xml 中无该SN配置项' ,showcolor=True)
            return False

        self.options = self.xml.get_options_element()
        self.options2 = self.xml.get_options2_element()

        #USB串口设备重新连接
        if self.dev1 and self.dev1.type == 'serial':
            if not self.dev1._active():
                tool.create_device(self.dev1.settings, self.pagewin1.win_idx, fail_skip=True)
                self.dev1, _ = Config.getdevice(self.pagewin1.win_idx)
                Config.update_device_status(self.pagewin1.win_idx, DeviceState.background)

        # USB串口设备重新连接
        if self.dev2 and self.dev2.type == 'serial':
            if not self.dev2._active():
                tool.create_device(self.dev2.settings, self.pagewin2.win_idx, fail_skip=True)
                self.dev2, _ = Config.getdevice(self.pagewin2.win_idx)
                Config.update_device_status(self.pagewin2.win_idx, DeviceState.background)

        customer_sn_value = 'NOT FOUND'
        if Config.mode['workorder_mode']:
            # 获取绑定信息
            self.bind_info = tool.get_bind_info_by_barcode(sn_value)
            customer_sn_value = tool.get_customer_sn_value(self.bind_info)

            if Config.worktable_loaded:
                assign_status, assign_msg = tool.assignMesAttrBySN(sn_value, self.mes_attr)
                if not Config.mode['repaire_mode']:
                    repair_status, repair_msg = tool.sn_in_repaire(self.mes_attr)
                    use_status, use_status_code, use_msg = tool.sn_in_procedurce(sn_value, self.mes_attr)
                    if not assign_status&repair_status&use_status:
                        msg = assign_msg + repair_msg + use_msg
                        self.section_message(msg, showcolor=True)
                        if use_status_code == 'AfterStatin':
                            msg_value = self.get_message_value('该条码{}已过站'.format(sn_value), '{}:已过站'.format(
                                self.pagewin1.GetName()), style=wx.OK | wx.CANCEL |wx.ICON_WARNING, data = {'okcancel':(u'重测', u'取消')})
                            if not msg_value:
                                return False
                        else:
                            return False

            # 根据工单 获取软件软件信息
            status, msg = tool.get_assign_version(self.dict, self.xml)
            if not status:
                self.section_message(msg, showcolor=True)
                return False

        #选择工序
        if Config.autoworkstage or Config.workstage_first:
            status, workstage_value = self.choose_workstage()
            if not status:
                return False
            else:
                Config.workstage_first = False
                Config.station_id = str(workstage_value)

        #工序弹框
        if not self.workstage_msgbox(Config.station_id, sn_value):
            return False

        #获取MES变量
        for key, value in self.mes_attr.iteritems():
            if key.startswith('@'):
                self.dict.update({key: value})

        #获取自定变量
        if self.xml.get_attribute_element() is not None:
            for item in self.xml.get_attribute_element():
                if item.attrib.has_key('station') and self.get_tag_value(item, 'station') == Config.station_id:
                    self.dict[item.get('name')] = self.get_tag_value(item, 'value')
                elif not item.attrib.has_key('station'):
                    self.dict[item.get('name')] = self.get_tag_value(item, 'value')

        self.section1.Clear()
        self.log1.Clear()
        if self.section2: self.section2.Clear()
        if self.log2: self.log2.Clear()
        Config.processhandler.truncate(0)
        Config.processhandler.seek(0)
        crcpasswd = tool.crc_passwd(self.dict['@MAC'])
        crcpasswd0 = tool.crc_passwd('00:00:00:00:00:00')
        self.dict.update({'@SN': sn_value.upper(), '@CSN': customer_sn_value.upper(), '@CRCPW':crcpasswd, '@CRCPW0':crcpasswd0})
        return True

    def run(self):
        result = PASS
        self._keepgoing = True
        try:
            with Config.lock:
                prepare_status = self.prepare()
                if prepare_status:
                    Config.popup[self.win_idx].update({'byhand':True})

                if not prepare_status:
                    Config.popup[self.win_idx].update({'byhand': False})
                    Config.update_device_status(self.pagewin1.win_idx, DeviceState.foreground)
                    if self.pagewin2:
                        Config.update_device_status(self.pagewin2.win_idx, DeviceState.foreground)
                    return

            start_time = datetime.now()
            self.status_text.SetLabel('')
            self.dev1_sn.SetLabel(self.dict['@SN'])
            self.devwin.SetBackgroundColour(Config.colour_aqua)
            self.devwin.Refresh()
            self.section_message('正在测试产品：{}'.format(self.product_name))

            for tree, item in self.xml.get_run_sequence():
                if tree.get(self.xml._run) == 'True' and self._keepgoing:
                    if self.get_tag_value(tree, 'station', 'unset') == Config.station_id:
                        item_ret = self.item_test(item, tree)
                        self.section_message(item_ret)
                        result = item_ret[1]
                        if result == FAIL: break

            end_time = datetime.now()
            diff_time = (end_time - start_time).seconds
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
            self.section_message('总用时：{}s'.format(diff_time))
            self.close(start_time, end_time, diff_time, result)
            self.postclose(result)
        except etree.XMLSyntaxError as e:
            self.section_message(u'配置文件格式错误:{}\n错误信息:{}'.format(e.filename, e.message), showcolor=True)
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            self.postclose(FAIL, True)
        except re.error  as e:
            self.section_message(u'正则表达式错误,错误信息：{}'.format(e.message), showcolor=True)
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            self.postclose(FAIL, True)
        except IOError as e:
            self.section_message(u'IOError: {}\n提示：文件路径不能包含中文和空格字符'.format(e.message), showcolor=True)
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            self.postclose(FAIL, True)
        except KeyError as e:
            self.section_message(u'文件:{} 变量异常(提示：变量未定义或引用异常): {}'.format(self.xml.file, e.message), showcolor=True)
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            self.postclose(FAIL, True)
        except Exception as e:
            self.section_message(u'脚本运行错误:{}'.format(tool.errorencode(traceback.format_exc())), showcolor=True)
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            self.postclose(FAIL, True)

    def item_test(self, item, tree, flag=True):
        item_stage_text = self.get_tag_value(tree, 'cn', None)
        if not item_stage_text: item_stage_text = tree.tag
        self.status_text.SetLabel('正在测试：{}'.format(item_stage_text))
        if flag: self.recored_process(content=tree.tag, type="mode_in")
        start_time, result = datetime.now(), PASS
        for cmd in item.getchildren():
            if cmd.tag == 'cmd':
                if self.cmd_test(cmd, item, tree) == FAIL:
                    result = FAIL; break
            elif cmd.tag == 'if':
                if_judge_result = self.item_test(cmd, tree, False)[1]
                if_item_test_result = self.if_item_test(cmd, if_judge_result, tree)
                if if_item_test_result == FAIL:
                    result = FAIL; break
            elif cmd.tag == 'for':
                value_list = self.get_tag_value(cmd, 'value')
                assign_name = cmd.get('assign', '@FOR_NONE')
                for assign_value in value_list.split(','):
                    self.dict[assign_name] = assign_value
                    result = self.item_test(cmd, tree, False)[1]
                    if result == FAIL: break

        end_time = datetime.now()
        diff_time = (end_time - start_time).seconds
        start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        if flag: self.recored_process(content=tree.tag, type="mode_out")
        return (item_stage_text, result, start_time, end_time, diff_time)

    def if_item_test(self, item, result, tree):
        if_item_result = None
        for child in item.getchildren():
            if result == PASS and child.tag == 'ok':
                if_item_result = self.item_test(child, tree, False)[1]
            elif result == FAIL and child.tag == 'fail':
                if_item_result = self.item_test(child, tree, False)[1]
        return if_item_result

    def cmd_test(self, cmd, item, tree):
        now = datetime.now()
        self.dict['@YEAR'] = now.year
        self.dict['@MONTH'] = now.month
        self.dict['@DAY'] = now.day
        self.dict['@HOUR'] = now.hour
        self.dict['@MINUTE'] = now.minute
        self.dict['@SEC'] = now.second
        self.dict['@NOW'] = '{}{:0>2}{:0>2}{:0>2}{:0>2}{:0>2}'.format(now.year, now.month, now.day, now.hour, now.minute, now.second)
        self.dict['@NOW1'] = '{} {} {} {} {} {}'.format(now.hour, now.minute, now.second, now.year, now.month, now.day)

        result, cmd_content = PASS, ''
        cmd_endflag = self.get_tag_value(cmd, 'endflag', '')
        cmd_type = self.get_tag_value(cmd, 'cmdtype', 'cmd')
        cmd_retrytime = self.get_tag_value(cmd, 'retry', '0')
        cmd_flag = self.get_tag_value(cmd, 'flag', '')
        cmd_timeout = float( self.get_tag_value(cmd, 'timeout', '10') )
        cmd_delay = float(self.get_tag_value(cmd, 'delay', '0'))
        cmd_str =  self.get_tag_value(cmd, 'command', '')
        cmd_to = self.get_tag_value(cmd, 'to', 'master')

        default_errormsg = None
        if cmd_type == 'cmd':
            default_errormsg = '检查 命令:{} 超时时间:{} 结束标志:{}'.format(cmd_str, cmd_timeout, cmd_endflag)
        else:
            default_errormsg = ''

        cmd_errormsg = self.get_tag_value(cmd, 'errormsg', default_errormsg)

        try:
            cmd_retrytime = int(cmd_retrytime)
            cmd_timeout = float(cmd_timeout)
        except ValueError as e:
            cmd_timeout, cmd_retrytime = 1 , 0

        if cmd_type == 'cmd':
            cmd_result, cmd_content = self.cmd_run(locals())
            verify_result = self.verify_result(cmd, cmd_content, item)
            if cmd_result == FAIL or verify_result.__contains__(FAIL):
                while cmd_retrytime > 0:
                    cmd_retrytime -= 1
                    cmd_result, cmd_content = self.cmd_run(locals())
                    verify_result = self.verify_result(cmd, cmd_content, item)
                    if cmd_result == PASS and not verify_result.__contains__(FAIL): break

            if cmd_result == FAIL or verify_result.__contains__(FAIL):
                result = FAIL
                if cmd_errormsg: self.section_message(cmd_errormsg, cmd_to, True)
        elif cmd_type == 'function':
            func = getattr(self, cmd_str)
            cmd_content, istimeout = func(cmd)
            if istimeout:
                if cmd_errormsg: self.section_message(cmd_errormsg, cmd_to,  True)
                result = FAIL
        elif cmd_type == 'dialog':
            with Config.lock:
                dlg_style = self.get_tag_value(cmd, 'style', '').strip().lower()
                caption = self.get_tag_value(cmd, 'caption', 'Info')
                style = wx.OK if dlg_style == 'ok' else  wx.OK | wx.CANCEL
                window = self.pagewin1 if cmd_to == 'master' else self.pagewin2
                msg_value = self.get_message_value(cmd_str, '{}:{}'.format(window.GetName(), caption), style|wx.ICON_INFORMATION)
                if not msg_value: result = FAIL
        elif cmd_type == 'device':
            with Config.lock:
                device_type = self.get_tag_value(cmd, 'type', '')
                if device_type == 'xet':
                    teleatt = instrument.TeleATT(self, item=cmd)
                    ret, self.telelog = teleatt.run()
                    if ret:
                        self.dict['@XET'] = PASS
                        self.dict['$XET'] = 'True'
                        result = PASS
                    else:
                        self.dict['@XET'] = FAIL
                        self.dict['$XET'] = 'False'
                        result = FAIL
                        if cmd_errormsg: self.section_message(cmd_errormsg, cmd_to, True)
        elif cmd_type == 'session':
            self.section_message(cmd_str, cmd_to)
        elif cmd_type == 'null':
            cmd_content = cmd_str
            verify_result = self.verify_result(cmd, cmd_content, item)
            if verify_result.__contains__(FAIL):
                result = FAIL
                if cmd_errormsg:
                    self.section_message(cmd_errormsg, cmd_to, True)
        elif cmd_type == 'msgbox':
            with Config.lock:
                cmd.attrib.update({'type': cmd_type})
                status, workstage_msgbox_value = self.get_self_define_value(cmd)
                self.dict.update(workstage_msgbox_value)
        elif cmd_type == 'sleep':
            exec 'time.sleep({})'.format(cmd_str)
        elif cmd_type == 'condition':
            s_keys_all = pd.Series(self.dict.keys())
            s_keys_dollar = s_keys_all[s_keys_all.str.startswith('$')]
            s_keys_at = s_keys_all[s_keys_all.str.startswith('@')]
            s_keys_mix = s_keys_dollar.append(s_keys_at, ignore_index=True)
            s_keys_mix = s_keys_mix.sort_values(ascending=False)
            for key in s_keys_mix.values:
                key_pattern = key.replace('$', '\$') if key.startswith('$') else key
                cmd_str = re.sub(key_pattern, str(self.dict[key]), cmd_str)
            result = PASS if eval(cmd_str) else FAIL
        elif cmd_type == 'item':
            for tree, item in self.xml.get_run_sequence():
                if tree.tag == cmd_str:
                    item_ret = self.item_test(item, tree)
                    self.section_message(item_ret, cmd_to)
                    result = item_ret[1]
                    break
        return result

    def cmd_run(self, others):
        cmd_content, result = '', PASS
        cmd_str = others.get('cmd_str')
        cmd_endflag = others.get('cmd_endflag')
        cmd_timeout = others.get('cmd_timeout')
        cmd_errormsg = others.get('cmd_errormsg')
        cmd_flag = others.get('cmd_flag')
        cmd_flag = cmd_flag.split('|')
        cmd_to = others.get('cmd_to')
        cmd_delay = others.get('cmd_delay')

        start_time = time.time()
        _dev, _options = (self.dev1, self.options) if cmd_to == 'master' else (self.dev2, self.options2)
        _linefeed = self.get_tag_value(_options, 'linefeed', '\n')
        _dev.set_read_timeout(0.2)

        if cmd_endflag is None:
            cmd_endflag_list = None
        else:
            cmd_endflag_list = [v.lower() for v in cmd_endflag.split('|') ]

        if 'hex' in cmd_flag:
            cmd_str = binascii.unhexlify(cmd_str)

        if 'detect' in cmd_flag:
            if 'char' in cmd_flag:
                for c_char in bytes(cmd_str):
                    time.sleep(cmd_delay)
                    self.write_cmd(_dev, bytes(c_char), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
            else:
                self.write_cmd(_dev, bytes(cmd_str), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
        else:
            if 'char' in cmd_flag:
                for c_char in bytes(cmd_str):
                    time.sleep(cmd_delay)
                    self.write_cmd(_dev, bytes(c_char), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
                time.sleep(cmd_delay)
                self.write_cmd(_dev, bytes(_linefeed), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
            else:
                self.write_cmd(_dev, bytes(cmd_str + _linefeed), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})

        while True:
            if time.time() - start_time > cmd_timeout:
                result = FAIL
                break

            if self._keepgoing == False:
                result = FAIL;cmd_content += '<Process Stoped>'; break;

            line = _dev.read_line(fix=True)
            line = self.log_message(line, cmd_to)
            cmd_content += line
            if '--more--' in line.lower(): self.write_cmd(_dev, bytes(' '))
            if cmd_endflag_list == None:
                result = PASS; break;
            elif cmd_endflag_list:
                flag = False
                for cmd_endflag_part in cmd_endflag_list:
                    if cmd_endflag_part in line.lower():
                        result = PASS; flag = True; break;
                if flag: break
            elif line == '':
                continue
        return (result, cmd_content)

    def highlight_match(self, match, cmd_content, which):
        _log = self.log1 if which == 'master' else self.log2
        try:
            if match == None: return
            style = wx.TextAttr('white', 'black')
            base_pos = _log.GetValue().find(cmd_content)
            match_relative_pos = match.span(1)
            match_absolute_pos = (match_relative_pos[0] + base_pos, match_relative_pos[1] + base_pos)
            _log.SetStyle(match_absolute_pos[0], match_absolute_pos[1], style)
        except Exception as e:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    def time_delta(self, time_str):
        time_search = re.search(r'(?P<date>\d{4}-\d{2}-\d{2}).+(?P<time>\d{2}:\d{2}:\d{2})', time_str)
        d = time_search.groups()[0].split('-')
        t = time_search.groups()[1].split(':')
        d1, d2, d3 = int(d[0]), int(d[1]), int(d[2])
        t1, t2, t3 = int(t[0]), int(t[1]), int(t[2])
        device_date = datetime(d1, d2, d3, t1, t2, t3)
        device_time_sec = time.mktime(device_date.timetuple())
        return time.mktime(time.localtime()) - device_time_sec

    def fan_regex(self, cmd, cmd_content, resultregex, item):
        ret = []
        cmd_to = self.get_tag_value(cmd, 'to', 'master')

        which_re = self.get_tag_value(resultregex, 'which_re', '')
        which_value = self.get_tag_value(resultregex, 'which_value', '')
        level_re = self.get_tag_value(resultregex, 'level_re', '')
        speed_re = self.get_tag_value(resultregex, 'speed_re', '')
        level = self.get_tag_value(resultregex, 'level', '')
        level_range = self.get_tag_value(resultregex, 'level_range', '')
        extra_re = self.get_tag_value(resultregex, 'extra_re', '')
        extra_value = self.get_tag_value(resultregex, 'extra_value', '')

        which_re_match = re.search(which_re, cmd_content)
        level_re_match = re.search(level_re, cmd_content)
        speed_re_match = re.search(speed_re, cmd_content)
        extra_re_match = re.search(extra_re, cmd_content)

        self.highlight_match(which_re_match, cmd_content, cmd_to)
        self.highlight_match(level_re_match, cmd_content, cmd_to)
        self.highlight_match(speed_re_match, cmd_content, cmd_to)
        self.highlight_match(extra_re_match, cmd_content, cmd_to)

        try:
            which_re_match_value = which_re_match.groups()[0]
            level_re_match_value = level_re_match.groups()[0]
            speed_re_match_value = speed_re_match.groups()[0]
            extra_re_match_value = extra_re_match.groups()[0]

            if which_re_match_value in which_value.split('|'):
                ret.append(PASS)
            else:
                self.section_message('{}校验错误: 实为:{} 现为:{}'.format(which_re, [which_re_match_value], [which_value]), cmd_to, showcolor=True)
                ret.append(FAIL)

            if extra_re_match_value in extra_value.split("|"):
                ret.append(PASS)
            else:
                self.section_message('{}校验错误: 实为:{} 现为:{}'.format(extra_re, [extra_re_match_value], [extra_value]), cmd_to, showcolor=True)
                ret.append(FAIL)

            level_idx = level.split(',').index(level_re_match_value)

            level_range_value = level_range.split(',')[level_idx]
            level_range_value = level_range_value.split('-')

            # int(match2.groups()[0]) >= int(value_range[0]) and int(match2.groups()[0]) <= int(value_range[0])
            if int(speed_re_match_value) in xrange(int(level_range_value[0]), int(level_range_value[1]) + 1):
                ret.append(PASS)
            else:
                error_msg = '风扇实际速度：{} 不在 {}-{}范围，风扇级别{}.'.format(speed_re_match_value, level_range_value[0],
                                                                  level_range_value[1], level_re_match_value)
                self.section_message(error_msg, cmd_to, showcolor=True)
                ret.append(FAIL)
        except Exception as e:
            ret.append(FAIL)
            self.section_message(etree.tostring(resultregex), cmd_to, showcolor=True)
            self.section_message(traceback.format_exc(), cmd_to, showcolor=True)
            Config.logger.error(tool.errorencode(traceback.format_exc()))
        finally:
            return FAIL if FAIL in ret else PASS

    def verify_result(self, cmd, cmd_content, item):
        result = []
        children = cmd.getchildren()
        cmd_type = self.get_tag_value(cmd, 'cmdtype', 'cmd')
        cmd_to = self.get_tag_value(cmd, 'to', 'master')

        if len(children) == 0 or cmd_type not in ['cmd', 'null']: return result;
        for resultregex in children:
            current_result = PASS
            assign_value = resultregex.attrib.get('assign', 'NULL')
            if resultregex.tag == 'fan':
                ret = self.fan_regex(cmd, cmd_content, resultregex, item)
                result.append(ret)
                self.dict[assign_value] = str(True) if ret == PASS else str(False)
                continue

            regex = self.get_tag_value(resultregex, 'regex', '')
            errormsg = self.get_tag_value(resultregex, 'errormsg', '')
            regex_flag = self.get_tag_value(resultregex, 'flag', '').split('|')
            # 添加默认 等于 标记
            if 'eq' not in regex_flag: regex_flag.append('eq')
            match = re.search(regex, cmd_content)

            if match:
                match_value = match.groups()[0]
            else:
                self.section_message('未校验：{}'.format(regex), cmd_to, showcolor=True)
                result.append(FAIL)
                self.dict[assign_value] = str(False)
                continue

            self.highlight_match(match, cmd_content, cmd_to)
            match_value = tool.convert_value(match_value, regex_flag)
            #匹配的值赋给该变量
            if resultregex.attrib.has_key('assignto'):
                self.dict[resultregex.attrib.get('assignto')] = match_value
            # 检测时间误差
            if 'time' in regex_flag:
                time_delta = self.time_delta(match_value)
                timedelta_permit = self.get_tag_value(resultregex, 'timedelta', '30')
                if int(timedelta_permit) < abs(time_delta):
                    self.section_message('FAIL：测试时间误差:{}s  允许时间误差:{}s'.format(time_delta, timedelta_permit), cmd_to, True)
                    self.dict[assign_value] = str(False)
                    result.append(FAIL)
                    current_result = FAIL
                else:
                    self.section_message('PASS：测试时间误差:{}s  允许时间误差:{}s'.format(time_delta, timedelta_permit), cmd_to)
                    self.dict[assign_value] = str(True)
                    result.append(PASS)
                    current_result = PASS

            value = None
            if resultregex.attrib.has_key('value'):
                value = self.get_tag_value(resultregex, 'value', '')
                value_list = value.split('|')
            elif resultregex.attrib.has_key('value_range'):
                value = self.get_tag_value(resultregex, 'value_range', '')
                value_min, value_max = value.split('-')
                if match_value.isdigit() and value_min.isdigit() and value_max.isdigit():
                    match_value, value_min, value_max = int(match_value), int(value_min), int(value_max)
                    value_list = xrange(value_min, value_max + 1)
                else:
                    value_list = None
            else:
                value_list = None

            if match:
                compare_flag = ''
                if value_list == None:
                    result.append(PASS)
                elif 'ne' in regex_flag:
                    if match_value in value_list:
                        compare_flag = 'ne'
                        result.append(FAIL)
                        current_result = FAIL
                elif 'lt' in regex_flag:
                    for target_value in value_list:
                        if not (tool.isfloat(match_value) and tool.isfloat(target_value)) or float(match_value) >= float(target_value):
                            compare_flag = 'lt'
                            result.append(FAIL)
                            current_result = FAIL
                            break
                elif 'le' in regex_flag:
                    for target_value in value_list:
                        if not (tool.isfloat(match_value) and tool.isfloat(target_value)) or float(match_value) > float(target_value):
                            compare_flag = 'le'
                            result.append(FAIL)
                            current_result = FAIL
                            break
                elif 'gt' in regex_flag:
                    for target_value in value_list:
                        if not (tool.isfloat(match_value) and tool.isfloat(target_value)) or float(match_value) <= float( target_value):
                            compare_flag = 'gt'
                            result.append(FAIL)
                            current_result = FAIL
                            break
                elif 'ge' in regex_flag:
                    for target_value in value_list:
                        if not (tool.isfloat(match_value) and tool.isfloat(target_value)) or float(match_value) < float( target_value):
                            compare_flag = 'ge'
                            result.append(FAIL)
                            current_result = FAIL
                            break
                elif 'eq' in regex_flag:
                    if match_value not in value_list:
                        compare_flag = 'eq'
                        result.append(FAIL)
                        current_result = FAIL

                if current_result == FAIL:
                    match_name = match.groupdict().keys()[0] if match.groupdict() else regex
                    if errormsg:
                        self.section_message(errormsg, showcolor=True)
                    else:
                        self.section_message( u'{}校验错误({}): 实为:{} 现为:{}'.format(match_name, compare_flag, [str(match_value)], value_list), showcolor=True)

        return result

    def record_message(self, start_time, end_time, diff_time, result, from_='master'):
        sn = mac = logprocess = logserial = guid = ''
        if from_ == 'master':
            sn = self.dict['@SN']
            mac = self.dict['@MAC']
            logserial = self.log1.GetValue() + self.telelog
            logprocess = self.section1.GetValue()
        else:
            sn = self.dict['B_SN']
            mac = self.dict['B_MAC']  if 'B_MAC' in self.dict else '00:00:00:00:00:00'
            logserial = self.log2.GetValue()
            logprocess = self.section2.GetValue()

        operator = Config.wn + '[{}]'.format(Config.wnname)
        logserial = logserial.replace("\"", "\\\"")
        logprocess = logprocess.replace("\"", "\\\"")
        workstage = Config.station_id
        if Config.worktable_loaded:
            product_name = self.mes_attr['extern_productname']
            product_type = self.mes_attr['extern_producttype']
            product_code = self.mes_attr['extern_productcode']
            product_version = self.mes_attr['extern_productversion']
            lotno = self.mes_attr['extern_lotno']
            bomcode = self.mes_attr['extern_bomcode']
            workorder = self.mes_attr.get('extern_WJTableName', '')
            subline = self.mes_attr.get('extern_SubLine', '')
            sql = "insert into sn_table(sn, result, starttime, endtime, totaltime, operator ,workorder, bomcode, productname, productver, lotno, guid, description, logserial, logprocess, segment1, segment2, segment3, segment4) " \
                  "values(\"{}\",\"{}\", \"{}\", \"{}\", \"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\", \"{}\", \"{}\", \"{}\",  \"{}\",  \"{}\") ".format(
                sn, result, start_time, end_time, str(diff_time), operator, workorder, bomcode, product_name, product_version, lotno, guid, 'remark', logserial, logprocess, mac, product_code, workstage, subline)
        else:
            sql = "insert into sn_table(sn, result, starttime, endtime, totaltime, operator, productname, guid, logserial, logprocess, segment1, segment3)" \
                  " values(\"{}\", \"{}\", \"{}\", \"{}\",\"{}\", \"{}\",\"{}\", \"{}\",\"{}\", \"{}\", \"{}\",  \"{}\" )".format(sn, result, start_time, end_time, str(diff_time), operator, self.product_name, guid, logserial, logprocess, mac, workstage)

        try:
            Config.db.execute(sql)
            Config.db.commit()
        except Exception as e:
            Config.db.rollback()
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    def mes_write(self, result):
        if result == FAIL: return False
        repair_status, repair_msg = tool.sn_in_repaire(self.mes_attr)
        use_status, use_status_code, use_msg = tool.sn_in_procedurce(self.mes_attr['extern_SN'] , self.mes_attr)
        if not (repair_status and use_status):
            msg = repair_msg + use_msg + ',不能重复过站'
            self.section_message(msg, showcolor=True)
            return True

        extern_SerialNumber = self.mes_attr['extern_SerialNumber']
        extern_WJTableName = self.mes_attr['extern_WJTableName']
        extern_SubLineCode = self.mes_attr['extern_SubLineCode']
        extern_stritemmemo = self.mes_attr['extern_stritemmemo']
        extern_work_done_status = self.mes_attr['extern_work_done_status']
        extern_strWorkCode2 = self.mes_attr['extern_strWorkCode2']
        extern_strmpk = self.mes_attr['extern_strmpk']
        extern_CompSendno = self.mes_attr['extern_CompSendno']
        extern_stritemtype = self.mes_attr['extern_stritemtype']
        extern_stritemversion = self.mes_attr['extern_stritemversion']
        extern_SubTestPosition = self.mes_attr['extern_SubTestPosition']
        extern_AttempterCode = self.mes_attr['extern_AttempterCode']
        extern_SubID = self.mes_attr['extern_SubID']
        extern_Num1 = self.mes_attr['extern_Num1']
        extern_ScanType = self.mes_attr['extern_ScanType']
        extern_SubAttemperCode = self.mes_attr['extern_SubAttemperCode']
        extern_stritemcode = self.mes_attr['extern_stritemcode']
        extern_CompSendmpk = self.mes_attr['extern_CompSendmpk']
        extern_SubLine = self.mes_attr['extern_SubLine']
        op_workers = self.mes_attr['op_workers']
        strRepair = self.mes_attr['extern_repair']

        strBarCode = self.mes_attr['extern_SN']
        strCompSendno = extern_CompSendno
        strCompSendmpk = extern_CompSendmpk

        sql = "SELECT name FROM  DMSNEW.view_workclasstype where  to_number(to_char(sysdate,'HH24'))  >= to_number(substr(describe,1,2)) " + \
              " and to_number(to_char(sysdate,'HH24')) < to_number(substr(describe,7,2))"
        sql_value = Config.mes_db.fetchall(sql)
        classname = tool.mes_value(sql_value[0][0])

        try:
            # write failed
            strbadposition = ''
            commonName = Config.wn + Config.wnname + '[AutoTest]'
            strType = u'备注'

            if result == FAIL:
                return
                # with THREAD_LOCK:
                #     evt = ThreadDialogEvent(win_idx=self.win_idx, type='BADCODE', data={})
                #     wx.PostEvent(self.win, evt)
                #     status, badvalue = self.data_queue.get()
                #     if not status: return None
                #     (strbadname, strbadtype, strType) = badvalue
                #     self.data_queue.task_done()
                #     repair_flag = 'yes'
            else:
                strbadname = strbadtype = strType = ''
                repair_flag = 'no'

            sql_station_out = "insert into " + "DMSNEW." + extern_WJTableName + "(subid,barcode,subattemper_code,line_code2,product_code,product_version,product_type,attempter_code,qulity_flag"
            sql_station_out  +=  ",qulity_plobolem,repair1,qualityposition,scan_position,mpk,produce_group,scan_person,aim_clint,testposition,describe,repair,segment2,sendno,sendmpk) values(" \
                                 + extern_SerialNumber + ",'" + strBarCode + "','" + extern_SubAttemperCode + "','" + extern_SubLine + "','" + extern_stritemcode + "','" + extern_stritemversion + "','" + \
                                 extern_stritemtype + "','" + extern_AttempterCode + "','" + repair_flag +"'" + ","
            sql_station_out += "'" + strbadname + "','" + strbadtype + "','" + strbadposition + "','L','" + extern_strmpk + "','" + classname + "','" + commonName + "','" \
                               + extern_strWorkCode2 + "','" + extern_SubTestPosition + "','" + strType + "','" + strRepair + "','" + extern_stritemmemo + "','" + strCompSendno + "','" + strCompSendmpk + "' ) "

            sql_station_in = "insert into " + "DMSNEW." + extern_WJTableName + \
                             "(subid, barcode, subattemper_code, line_code2 ,product_code,product_version,product_type,attempter_code,produce_group,mpk,scan_person, aim_clint, testposition,segment2,  sendno,sendmpk)  values(" \
                             + extern_SerialNumber + ",'" + strBarCode + "','" + extern_SubAttemperCode + "','" + extern_SubLineCode + "','" + \
                             extern_stritemcode + "','" + extern_stritemversion + "','" + extern_stritemtype + "','" + extern_AttempterCode + \
                             "','" + classname + "','" + extern_strmpk + "','" + commonName + "','" + extern_strWorkCode2 + "','" + \
                             extern_SubTestPosition + "','" + extern_stritemmemo + "','" + strCompSendno + "','" + strCompSendmpk + "' )"

            #step 1, 2
            Config.mes_db.commit()
            Config.mes_db.execute(sql_station_in)
            Config.mes_db.execute(sql_station_out)

            #step 3
            sql_update_main_barcode = " UPDATE  DMSNEW.WORK_MAIN_BARCODE  SET  NUMR=(numr+2), OUT_TIME=sysdate where  BARCODE='" + strBarCode + "'   "
            Config.mes_db.execute(sql_update_main_barcode)

            sql = "select (select count(distinct(barcode)) from dmsnew.{worktable} where subattemper_code='{sub_attemper_table}'),  " \
                  "(select nvl(sum(decode(qulity_flag||scan_type||segment13,'no正常生产no',1,0)),0) from dmsnew.{worktable} b where " \
                  "(b.barcode,b.scan_time) in(select barcode,max(scan_time) from dmsnew.{worktable} where subattemper_code='{sub_attemper_table}' " \
                  "group by barcode ) and subattemper_code='{sub_attemper_table}' and qulity_flag='no' and scan_type='正常生产' and scan_position='L' " \
                  "and segment13='no' )  from dual".format(worktable=extern_WJTableName, sub_attemper_table=extern_SubAttemperCode)
            sql_value = Config.mes_db.fetchone(sql)
            if sql_value:
                strCount1, strCount2 = sql_value[0], sql_value[1]
                if strCount2 > strCount1:
                    strCount2 = strCount1

            #extern_Num1  安排加工数
            if (extern_Num1 <= strCount2):
                sql = "update DMSNEW.mtl_sub_attemper set state= '已完工',rea_begin_date=nvl(rea_begin_date,sysdate),rea_end_date=sysdate, " \
                      "LINE_HEAD_NUM=({0}), ine_last_num=({0}),TOTALSENDNUM ={1}  where sub_attempter_code='{2}' ".format(extern_Num1, op_workers, extern_SubAttemperCode)
                Config.mes_db.execute(sql)
                if (extern_work_done_status == 0):
                    sql = "update DMSNEW.mtl_attemper set state='已完工',rea_begin_date=nvl(rea_begin_date,sysdate),real_finish_date=sysdate where attemper_code='" + extern_AttempterCode + "'"
                    Config.mes_db.execute(sql)

                    sql = "update DMSNEW.work_workjob set  STATE='已完工',rea_first_date=nvl(rea_first_date,sysdate),rea_last_date=sysdate where  workjob_code='" + extern_WJTableName + "'"
                    Config.mes_db.execute(sql)
            else:
                sql = "update DMSNEW.mtl_sub_attemper set STATE='已开工',rea_begin_date=nvl(rea_begin_date,sysdate),rea_end_date=null, " \
                      "LINE_HEAD_NUM=('{0}'), ine_last_num=('{1}'),TOTALSENDNUM={2}  where  sub_attempter_code='{3}'".format(strCount1, strCount2, op_workers, extern_SubAttemperCode)
                Config.mes_db.execute(sql)

                sql = "update DMSNEW.mtl_attemper set state='已开工',rea_begin_date=nvl(rea_begin_date,sysdate),real_finish_date=null where attemper_code='" + extern_AttempterCode + "'"
                Config.mes_db.execute(sql)

                sql = "update DMSNEW.work_workjob set  state='已开工',rea_first_date=nvl(rea_first_date,sysdate),rea_last_date=null where workjob_code='" + extern_WJTableName + "'"
                Config.mes_db.execute(sql)
        except Exception as e:
            Config.mes_db.rollback()
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            return None
        else:
            Config.mes_db.commit()
            self.section_message('{}自动过站成功'.format(strBarCode), showcolor=True)
            return  False if repair_flag == 'yes' else True

