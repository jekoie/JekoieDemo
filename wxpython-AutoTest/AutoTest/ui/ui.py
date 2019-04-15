#coding:utf-8
import functools
import wx
import wx.adv
import queue
import ftputil.error
import re
import os
import sys
import wx.lib.dialogs
import wx.lib.scrolledpanel as SP
import traceback
import ftfy
from wx.lib.pdfviewer import pdfViewer, pdfButtonPanel
import  wx.lib.mixins.listctrl  as  listmix
from wx.lib.pubsub import pub
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import threading
import socket
import time
import wx.lib.filebrowsebutton as filebrowse
import ftputil
from product.product import Product, EVT_THREAD_DIALOG
from lxml import etree
import pandas as pd
import wx.lib.newevent
import binascii
import tftpy
import arrow
import platform
from collections import deque
from serial import serialutil
from wx.py import shell
from serial.tools.list_ports import comports
from wx.lib.splitter import MultiSplitterWindow
from config.config import Config, DeviceState
import wx.lib.filebrowsebutton as filebrowse
from . import tool

def mes_value(value):
    mes_value =  '' if value == None else  ftfy.fix_text( unicode(str(value), errors='ignore') )
    return mes_value

class Validator(wx.Validator):
    def __init__(self, type):
        wx.Validator.__init__(self)
        self.type = type

    def Clone(self):
        return Validator(self.type)

    def Validate(self, parent):
        win = self.GetWindow()
        value = win.GetValue()
        if self.type == 'ip':
            valid_ip_re = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
            if re.match(valid_ip_re, value):
                return True
        elif self.type == 'number':
            if value.isdigit():
                return True

        win.SetBackgroundColour('pink')
        win.SetFocus()
        win.Refresh()
        return False

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

class TelnetSettingDialog(wx.Dialog):
    attrs = {'ip': '192.168.1.1', 'port': '23', 'name': None, 'protocol':'telnet'}
    def __init__(self, parent,  titile=u'Telent端口设置'):
        wx.Dialog.__init__(self, parent=parent, title=titile)
        # (serial.Serial attribute, label text, choice selection list)
        ip, port = self.attrs['ip'], self.attrs['port']
        self.ip_label = wx.StaticText(self, label='IP地址：')
        self.ip_input = wx.TextCtrl(self, -1, value= ip, validator=Validator(type='ip'))

        self.port_label = wx.StaticText(self, label='端口：')
        self.port_input = wx.TextCtrl(self, -1, value= port, size=(50, -1), validator=Validator(type='number'))

        host_sizer = wx.BoxSizer(wx.HORIZONTAL)
        host_sizer.Add(self.ip_label, 0, wx.LEFT | wx.EXPAND, 5)
        host_sizer.Add(self.ip_input, 0, wx.RIGHT| wx.EXPAND, 5)
        host_sizer.Add(self.port_label, 0, wx.RIGHT|wx.EXPAND)
        host_sizer.Add(self.port_input, 0, wx.EXPAND)

        # ok, cancel button
        okay = wx.Button(self, wx.ID_OK)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL)
        btsz = wx.StdDialogButtonSizer()
        btsz.AddButton(okay)
        btsz.AddButton(cancel)
        btsz.Realize()

        # place two sizer in vertical style
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(host_sizer, 0, wx.GROW)
        sizer.Add(btsz, 0, wx.GROW|wx.TOP, 5)
        self.SetSizerAndFit(sizer)

    def GetValue(self):
        self.__class__.attrs['ip'] = self.ip_input.GetValue().strip()
        self.__class__.attrs['port'] = self.port_input.GetValue().strip()
        self.__class__.attrs['name'] = '{}:{}'.format(self.attrs['ip'], self.attrs['port'])
        return self.__class__.attrs

#端口设置
class SerialSettingDialog(wx.Dialog):
    attrs = {'name': 'COM', 'stopbits': '1', 'bytesize': '8', 'timeout': '1',  'parity': 'N', 'baudrate': '9600', 'protocol':'serial' }
    def __init__(self, parent,  titile=u'串口设置'):
        wx.Dialog.__init__(self, parent=parent, title=titile)
        #(serial.Serial attribute, label text, choice selection list)
        wsz = [100, -1]

        port_pair = ('name', '端口：', [d.device for d  in list(comports()) ], 0)
        baudrate_pair = ('baudrate', '波特率：', ['9600', '115200'], 0)
        option_sizer = wx.FlexGridSizer(cols=6, hgap=6, vgap=6)

        for name, text, choices, default_sel in [port_pair, baudrate_pair]:
            label = wx.StaticText(self, label=text)
            choice = wx.Choice(self, choices=choices, size=wsz, name=name)
            choice.SetStringSelection(self.__class__.attrs[name])
            choice.Bind(wx.EVT_CHOICE, self.OnChoice)

            option_sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER)
            option_sizer.Add(choice, 0, wx.ALL | wx.ALIGN_CENTER)

        #ok, cancel button
        okay = wx.Button(self, wx.ID_OK)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL)
        btsz = wx.StdDialogButtonSizer()
        btsz.AddButton(okay)
        btsz.AddButton(cancel)
        btsz.Realize()

        #place two sizer in vertical style
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(option_sizer, 0, wx.GROW)
        sizer.Add(btsz, 0, wx.GROW)
        self.SetSizerAndFit(sizer)

    def OnChoice(self, evt):
        obj = evt.GetEventObject()
        attr_name, attr_value = obj.GetName(), evt.GetString()
        self.__class__.attrs[attr_name] = attr_value

    def GetValue(self):
        return self.__class__.attrs


def settingdialog_factory(window, type):
    if type == 'telnet':
        return TelnetSettingDialog(window)
    elif type == 'serial':
        return SerialSettingDialog(window)

class ListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

#显示测试流程信息
class SectionWindow(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, parent):
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent=parent)
        self.section_log = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.section_log, 1, wx.GROW)
        self.SetSizerAndFit(sizer)

    def Clear(self):
        self.section_log.Clear()

#显示串口信息和测试流程信息
class MessageWindow(wx.SplitterWindow):
    def __init__(self, parent):
        wx.SplitterWindow.__init__(self, parent=parent)
        self.parent = parent
        #when a period end, show process info
        self.section_window = SectionWindow(self)
        #串口信息控件
        self.log_area = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE |wx.TE_READONLY| wx.TE_RICH|wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER)
        self.log_area.Bind(wx.EVT_CHAR, self.OnChar)
        self.log_area.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.log_area.Bind(wx.EVT_KEY_UP, self.OnkeyUp)
        self.log_area.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        #split it and set minium size
        self.SplitHorizontally(self.section_window, self.log_area)
        self.SetMinimumPaneSize(50)
        self.SetSashPosition(150)

        self.pressed_key = None
        self.last_line = ''
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnCharHook(self, evt):
        keycode, keychar = evt.GetKeyCode(), unichr(evt.GetKeyCode())
        dev, status = Config.getdevice(self.parent.win_idx)
        if keycode == wx.WXK_TAB:
            dev.write(bytes(keychar))
        else:
            evt.DoAllowNextEvent()

    def OnkeyUp(self, evt):
        keycode, keychar = evt.GetKeyCode(), unichr(evt.GetKeyCode())
        dev, status = Config.getdevice(self.parent.win_idx)
        if self.pressed_key == wx.WXK_CONTROL and keychar == '6' and status == DeviceState.foreground and dev.alive():
            dev.write(binascii.unhexlify("1e"))

        self.pressed_key = None
        evt.Skip()

    def OnKeyDown(self, evt):
        keycode, keychar = evt.GetKeyCode(), unichr(evt.GetKeyCode())
        self.pressed_key = keycode
        evt.Skip()

    def OnChar(self, evt):
        keycode, keychar = evt.GetKeyCode(), unichr(evt.GetKeyCode())
        dev, status = Config.getdevice(self.parent.win_idx)
        if status == DeviceState.foreground and dev.alive():
            if keycode == wx.WXK_UP:
                dev.write('\x1b[A')
            elif keycode == wx.WXK_DOWN:
                dev.write('\x1b[B')
            # elif keycode == wx.WXK_LEFT:
            #     dev.write('\x1b[D')
            # elif keycode == wx.WXK_RIGHT:
            #     dev.write('\x1b[C')
            elif keycode == wx.WXK_RETURN:
                dev.write(bytes(self.parent.linefeed))
            else:
                dev.write(bytes(keychar))

        if dev and dev.type == 'telnet':
            self.log_area.AppendText(bytes(keychar))
        evt.Skip()

    def OnIdle(self, evt):
        dev, status = Config.getdevice(self.parent.win_idx)
        try:
            if dev and status == DeviceState.foreground and dev.alive():
                data =  dev.read_available()
                data = ftfy.fix_text(unicode(data, errors='ignore'), remove_control_chars=False)

                if data:
                    self.log_area.AppendText(data)
                    self.last_line += data
                    if '\n' in self.last_line:
                        self.last_line = self.last_line[self.last_line.rindex('\n')+1:]

                    if '\x08' in self.last_line:
                        origin_line = self.last_line
                        self.last_line = tool.back_remove(self.last_line)

                        self.log_area.Replace(self.log_area.GetLastPosition() - len(origin_line) ,self.log_area.GetLastPosition(), self.last_line )
        except serialutil.SerialException:
            Config.logger.error(tool.errorencode(traceback.format_exc()))
            tool.create_device(dev.settings, self.parent.win_idx, fail_skip=True)

class DevicePage(wx.Panel):
    def __init__(self, parent, name='', win_idx=None):
        wx.Panel.__init__(self, parent)
        #page index number and linefeed style
        self.win_idx = win_idx
        self.linefeed = Config.linefeed_cr
        #widget size
        wsz = [103, -1]
        ###############################################top area#####################################################
        #command enter area
        self.input_label = wx.StaticText(self, -1, u'输入:')
        self.input_text = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnCommandEnter, self.input_text)

        #linefeed selector
        self.linefeed_choice = wx.Choice(self, -1, choices=['LF', 'CR', 'CR/LF', 'None'], size=(wsz[0]/2, -1))
        self.linefeed_choice.SetStringSelection('CR')
        self.Bind(wx.EVT_CHOICE, self.OnLinefeed, self.linefeed_choice)

        # top sizer include input label,input text entry and linefeed choice , place top of the sizer
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.input_label, 0, wx.RIGHT | wx.ALIGN_CENTER, 8)
        top_sizer.Add(self.input_text, 1, wx.RIGHT | wx.GROW, 8)
        top_sizer.Add(self.linefeed_choice, 0, wx.RIGHT, 5)
        ##########################################top area#########################################################

        #########################################mid area##############################################################
        #mid szier place message window in middle
        message_win = MessageWindow(self)
        mid_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mid_sizer.Add(message_win, 1, wx.GROW)
        self.log_area = message_win.log_area
        self.section_area = message_win.section_window.section_log
        #########################################mid area##############################################################

        #########################################botton area############################################################
        #bottom sizer include clear button that place the bottom of the sizer
        bottom_item_size = (-1, 25)
        self.bottom_sizer = bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.clear_bn = wx.Button(self, -1, u'清除', size=bottom_item_size)
        self.tip_text = wx.StaticText(self, label='', style=wx.ALIGN_CENTRE_HORIZONTAL, size=bottom_item_size)
        self.tip_text.SetForegroundColour(wx.BLUE)
        self.time_text = wx.StaticText(self, label='2012-12-12 12:12:12 星期一', size=bottom_item_size)
        self.Bind(wx.EVT_BUTTON, self.OnClear, self.clear_bn)

        bottom_sizer.Add(self.clear_bn, 0, wx.ALIGN_BOTTOM)
        bottom_sizer.Add(self.tip_text, 1, wx.EXPAND|wx.ALIGN_BOTTOM)
        bottom_sizer.Add(self.time_text, 0, wx.ALIGN_BOTTOM)
        bottom_sizer.SetMinSize((-1, 3))
        #create timer and show current clock on time_text
        self.timer = wx.Timer(self)
        self.timer.Start(1000)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        #########################################bottom area############################################################

        #main sizer place top, middele, bottom sizer in vertical style
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(top_sizer,0, wx.GROW|wx.TOP|wx.BOTTOM, 2)
        mainsizer.Add(mid_sizer,1, wx.GROW|wx.TOP|wx.BOTTOM, 2)
        mainsizer.Add(bottom_sizer, 0, wx.EXPAND)
        self.SetSizer(mainsizer)

        #bind idle event; when app in idle status, it will read  serial and append to log area
        # self.Bind(wx.EVT_IDLE, self.OnIdle)
        pub.subscribe(self.OnDBChange, Config.topic_db_change)
        pub.subscribe(self.OnSetWindow, Config.topic_set_window)

    def OnSetWindow(self, win_idx, data):
        if self.win_idx == win_idx:
            if data['topic'] == 'setname':
                namectl, pos, protocol = data['namectl'], data['pos'], data['protocol']
                device, _ = Config.getdevice(self.win_idx)
                if device: device.close()
                with settingdialog_factory(self, protocol) as dlg:
                    dlg.SetPosition(pos)
                    if dlg.ShowModal() == wx.ID_OK:
                        device_settings = dlg.GetValue()
                        tool.create_device(device_settings, self.win_idx)
                        #设置控件名,窗体名
                        namectl.SetLabel(device_settings.get('name'))
                        #写设置到文件
                        tree = etree.parse(Config.devfile, Config.parser_without_comments)
                        root = tree.getroot()
                        node = root.find("./li[@win='{}']".format(self.win_idx))
                        if node is None:
                            node = etree.SubElement(root, 'li', {'win': str(self.win_idx)})
                        node.attrib.update(device_settings)
                        tree.write(Config.devfile, encoding='utf-8', pretty_print=True, xml_declaration=True)
                        #设置页名
                        notebook = self.GetParent()
                        self.SetName(device_settings['name'])
                        notebook.SetPageText(win_idx, device_settings['name'])
                        notebook.SetSelection(win_idx)
            elif data['topic'] == 'disconnect':
                dev, _ = Config.getdevice(win_idx)
                if dev: dev.close()
            elif data['topic'] == 'reconnect':
                try:
                    dev, _ = Config.getdevice(win_idx)
                    dev.connect()
                except Exception as e:
                    self.section_area.AppendText(u'{}重新连接失败\n'.format(self.GetName()))
                else:
                    self.section_area.AppendText(u'{}重新连接成功\n'.format(self.GetName()))

    def OnDBChange(self):
        msg_condition, msg = (Config.mode['debug_mode'], Config.mode['repaire_mode']) , ''
        if msg_condition == (True, True):
            msg = '已连接到测试数据库(维修账号)'
        elif msg_condition == (True, False):
            msg = '已连接到测试数据库'
        elif msg_condition == (False, True):
            msg = '维修账号'
        elif msg_condition == (False, False):
            msg = ''

        self.tip_text.SetLabelText(msg)
        self.bottom_sizer.Layout()

    def OnTimer(self, evt):
        try:
            self.time_text.SetLabel( arrow.now().format('YYYY-MM-DD HH:mm:ss dddd', locale='zh_cn') )
        except wx.PyAssertionError as e:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    #event of clear button in bottom sizer
    def OnClear(self, evt):
        self.log_area.Clear()
        self.section_area.Clear()

    #event of input entry in top sizer
    def OnCommandEnter(self, evt):
        obj = evt.GetEventObject()
        dev, status = Config.getdevice(self.win_idx)
        try:
            if dev and status == DeviceState.foreground and dev.alive():
                dev.write(bytes(obj.GetValue()+self.linefeed) )
        except Exception as e:
            Config.logger.error(tool.errorencode(traceback.format_exc()))
        finally:
            obj.Clear()

    def OnLinefeed(self, evt):
        feed = evt.GetString()
        if feed == 'LF':
            self.linefeed = Config.linefeed_lf
        elif feed == 'CR':
            self.linefeed = Config.linefeed_cr
        elif feed == 'CR/LF':
            self.linefeed = Config.linefeed_crlf
        elif feed == 'None':
            self.linefeed = Config.linefeed_none
        else:
            pass

class DeviceWindow(wx.Panel):
    def __init__(self, parent, name='', win_idx=None):
        wx.Panel.__init__(self, parent=parent, name=name)
        self.win_idx = win_idx
        # 线程
        self.thread = None
        self.thread_queue = queue.Queue(1)

        #绑定事件
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnShowPopupMenu)
        # 线程对话框
        self.Bind(EVT_THREAD_DIALOG, self.OnThreadDialog)

    def OnShowPopupMenu(self, evt): pass

    def OnThreadDialog(self, evt):
        if self.win_idx == evt.win_idx and evt.type == 'SN':
            self.thread_queue.put(tool.getSNValue(evt.data['win']))
        elif self.win_idx == evt.win_idx and evt.type == 'MAC':
            self.thread_queue.put( tool.getMacValue(evt.data['win']) )
        elif self.win_idx == evt.win_idx and evt.type == 'WORKSTAGE': #工序选择弹框
            win, xml = evt.data['win'], evt.data['xml']
            self.thread_queue.put( tool.getWorkstage(win, xml) )
        elif self.win_idx == evt.win_idx and evt.type == "WORKSTAGE_MSGBOX": #工序需要弹出哪些输入框
            win, item = evt.data['win'], evt.data['item']
            self.thread_queue.put(tool.getWorkstageMsgBox(win, item))
        elif self.win_idx == evt.win_idx and evt.type == 'MESSAGE':
            win, msg, caption, style, data = evt.win, evt.msg, evt.caption, evt.style, evt.data
            self.thread_queue.put(tool.getMessageDialog(win, msg, caption, style, data))

    def WorkTableLoaded(self):
        if not Config.worktable_loaded:
            mainframe = wx.Window.FindWindowByName('MainFrame')
            mainframe.OnJobInfo(mainframe, None)
        return Config.worktable_loaded

    def OnUnitTest(self, evt):

        product_dict = {'@WN': Config.wn, '@AGINGTIME': Config.agetime}
        product_dict['@SSID'] = '@{}_{}'.format(platform.node(), self.GetName())
        product_dict['@PORTID'] = str(100 + self.win_idx)
        product_dict['@VMAC'] = tool.inttomac(self.win_idx + 1)

        #工单模式加载工单号，非工单模式不加载工单
        if Config.mode['workorder_mode']:
            if not self.WorkTableLoaded(): return
        product = Product(product_dict, self.thread_queue, self)
        self.thread = threading.Thread(target=product.run, name=self.GetName() )
        self.thread.start()
        setattr(self.thread, 'stop', product.stop)

        pagewin = Config.windows[self][0]
        notebook = pagewin.GetParent()
        notebook.SetSelection(pagewin.win_idx)

#DeviceWinow to show port, stage, status info etc,
class SingleDeviceWindow(DeviceWindow):
    def __init__(self, parent,  name='', win_idx=None):
        super(self.__class__, self).__init__(parent, name, win_idx)

        self.dev1_name = wx.StaticText(self, -1, self.GetName(), pos=(10, 10))
        self.dev1_sn = wx.StaticText(self, -1, 'SN', pos=(10, 30))
        self.status_text = wx.StaticText(self, -1, '', pos=(10, 50))

        for st in [self.dev1_sn, self.dev1_name, self.status_text]:
            st.SetForegroundColour(Config.colour_black)
            st.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)
            st.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, encoding=wx.FONTENCODING_SYSTEM))

    def OnShowPopupMenu(self, evt):
        menu = wx.Menu()
        click_position = evt.GetPosition()
        option_item = menu.Append(-1, u'单元设置' )
        stop_item = menu.Append(-1, u'停止')
        setting_item = menu.Append(-1, u'设置' )
        dissconect_item = menu.Append(-1, u'断开连接')
        reconnect_item = menu.Append(-1, u'重新连接')

        #设置
        self.Bind(wx.EVT_MENU, functools.partial(self.OnPortSet, position=click_position), setting_item)
        self.Bind(wx.EVT_MENU, self.OnStop, stop_item)
        self.Bind(wx.EVT_MENU, self.OnReconnect, reconnect_item)
        self.Bind(wx.EVT_MENU, self.OnDisconnect, dissconect_item)
        option_item.Enable(False)
        self.PopupMenu(menu)

    def OnStop(self, evt):
        self.thread.stop()

    def OnReconnect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx, data={'topic': 'reconnect'})

    def OnDisconnect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx, data={'topic': 'disconnect'})

    def OnPortSet(self, evt, position):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx, data={ 'namectl': self.dev1_name,
            'topic': 'setname', 'pos': position, 'protocol': Config.protocol} )

    def OnUnitTest(self, evt):
        super(self.__class__, self).OnUnitTest(evt)
        #选择主设备页
        pagewin = Config.windows[self][0]
        notebook = pagewin.GetParent()
        notebook.SetSelection(pagewin.win_idx)

class DoubleDeviceWindow(DeviceWindow):
    def __init__(self, parent,  name='', win_idx=None):
        super(self.__class__, self).__init__(parent, name, win_idx)
        # 控件
        _startx, _starty, _stepy = 10, 10, 20
        self.dev1_label = wx.StaticText(self, label='主：', pos=(_startx, _starty))
        self.dev2_label = wx.StaticText(self, label='从：', pos=(_startx, _starty + _stepy))

        self.dev1_name = wx.StaticText(self, label='主设备', pos=(_startx + self.dev1_label.GetSize()[0] + 5, _starty))
        self.dev2_name = wx.StaticText(self, label='从设备', pos=(_startx + self.dev2_label.GetSize()[0] + 5, _starty + _stepy))

        self.dev1_sn_label = wx.StaticText(self, -1, '主SN：', pos=(_startx, _starty + _stepy*2 ))
        self.dev1_sn = wx.StaticText(self, -1, 'SN', pos=(_startx + self.dev1_sn_label.GetSize()[0] + 5, _starty + _stepy*2 ))

        self.status_text = wx.StaticText(self, -1, 'STATUS', pos=(_startx, _starty + _stepy*3))

        for st in [self.dev1_label, self.dev2_label, self.dev1_name, self.dev2_name, self.dev1_sn_label, self.dev1_sn, self.status_text]:
            st.SetForegroundColour(Config.colour_black)
            st.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)
            st.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, encoding=wx.FONTENCODING_SYSTEM))

    def OnShowPopupMenu(self, evt):
        menu = wx.Menu()
        click_position = evt.GetPosition()

        option_item = menu.Append(-1, u'单元设置')
        option_item.Enable(False)

        setting_submenu = wx.Menu()
        dev1_setting_item = setting_submenu.Append(-1, '设置主设备')
        dev2_setting_item = setting_submenu.Append(-1, '设置从设备')

        self.Bind(wx.EVT_MENU, functools.partial(self.OnDev1Set, position=click_position), dev1_setting_item)
        self.Bind(wx.EVT_MENU, functools.partial(self.OnDev2Set, position=click_position), dev2_setting_item)

        menu.AppendSubMenu(setting_submenu, '设置')

        stop_item = menu.Append(-1, '停止')
        self.Bind(wx.EVT_MENU, self.OnStop, stop_item)

        dissconect_submenu = wx.Menu()
        dissconect_dev1_item = dissconect_submenu.Append(-1, '断开主设备')
        dissconect_dev2_item = dissconect_submenu.Append(-1, '断开从设备')
        dissconect_all_dev_item = dissconect_submenu.Append(-1, '断开主从设备')
        self.Bind(wx.EVT_MENU, self.OnDev1Disconnect, dissconect_dev1_item)
        self.Bind(wx.EVT_MENU, self.OnDev2Disconnect, dissconect_dev2_item)
        self.Bind(wx.EVT_MENU, self.OnAllDisconnect, dissconect_all_dev_item)
        menu.AppendSubMenu(dissconect_submenu, '断开')

        connect_submenu = wx.Menu()
        connect_dev1_item = connect_submenu.Append(-1, '连接主设备')
        connect_dev2_item = connect_submenu.Append(-1, '连接从设备')
        connect_all_dev_item = connect_submenu.Append(-1, '连接主从设备')
        self.Bind(wx.EVT_MENU, self.OnDev1Connect, connect_dev1_item)
        self.Bind(wx.EVT_MENU, self.OnDev2Connect, connect_dev2_item)
        self.Bind(wx.EVT_MENU, self.OnAllConnect, connect_all_dev_item)
        menu.AppendSubMenu(connect_submenu, '连接')

        self.PopupMenu(menu)

    def OnStop(self, evt):
        self.thread.stop()

    def OnDev1Set(self, evt, position):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2,
                        data={'namectl': self.dev1_name, 'topic': 'setname', 'pos': position,'protocol': Config.protocol})

    def OnDev2Set(self, evt, position):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2+1,
                        data={'namectl': self.dev2_name, 'topic': 'setname', 'pos': position, 'protocol': Config.protocol})

    def OnDev1Disconnect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2, data={'topic': 'disconnect'})

    def OnDev2Disconnect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2+1, data={'topic': 'disconnect'})

    def OnAllDisconnect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx * 2, data={'topic': 'disconnect'})
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx * 2 + 1, data={'topic': 'disconnect'})

    def OnDev1Connect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2, data={'topic': 'reconnect'})

    def OnDev2Connect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2+1, data={'topic': 'reconnect'})

    def OnAllConnect(self, evt):
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2, data={'topic': 'reconnect'})
        pub.sendMessage(Config.topic_set_window, win_idx=self.win_idx*2+1, data={'topic': 'reconnect'})


def devicewindow_factory(type, parent, name, win_idx):
    if type == 'single':
        return SingleDeviceWindow(parent, name, win_idx)
    elif type == 'double':
        return DoubleDeviceWindow(parent, name, win_idx)

class SettingFrame(wx.Frame):
    def __init__(self, parent, title='', size=wx.DefaultSize):
        super(SettingFrame, self).__init__( parent=parent, title=title, size=size)
        self.SetIcon(wx.Icon(Config.logofile))
        self.main_panel = wx.Panel(self)
        self.statusbar = wx.StatusBar(self)
        self.SetStatusBar(self.statusbar)

        #显示方式--sizer
        viewer_sizer = self.viewer_sizer(self.main_panel)

        #协议
        protocol_sizer = self.protocol_sizer(self.main_panel)

        #窗体定位
        adj_sizer = self.adjustpos_sizer(self.main_panel)
        #其他--sizer
        other_boxsizer = self.other_sizer(self.main_panel)

        #
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(viewer_sizer, 0, wx.EXPAND)
        main_sizer.Add(protocol_sizer, 0, wx.EXPAND)
        main_sizer.Add(adj_sizer, 0, wx.EXPAND)
        main_sizer.Add(other_boxsizer, 0, wx.EXPAND)
        self.main_panel.SetSizer(main_sizer)

    def other_sizer(self, main_panel):
        panel = main_panel
        other_boxsizer = wx.StaticBoxSizer(wx.VERTICAL, panel, u"其他设置")

        # aging_sizer = self.aging_time_sizer(self.main_panel)
        win_nums_sizer = self.win_nums_sizer(self.main_panel)
        # xinertai_sizer = self.xinertai_sizer(self.main_panel)

        other_boxsizer.Add(win_nums_sizer, 0, wx.EXPAND | wx.BOTTOM)
        # other_boxsizer.Add(xinertai_sizer, 0, wx.EXPAND | wx.BOTTOM)

        return other_boxsizer


    def protocol_sizer(self, main_panel):
        panel = main_panel
        box = wx.RadioBox(panel, -1, '类型', choices=[u'Serial', u'Telnet'], name='protocol')
        if Config.protocol == 'serial':
            box.SetSelection(0)
        elif Config.protocol == 'telnet':
            box.SetSelection(1)
        box.Bind(wx.EVT_RADIOBOX, self.OnProtocolSelect)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(box, 0, wx.EXPAND)
        return sizer

    def adjustpos_sizer(self, main_panel):
        panel = main_panel
        adj_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, u"弹框定位")
        item_sizer = wx.BoxSizer(wx.HORIZONTAL)

        adj_enable_item = wx.CheckBox(panel, label=u'启用')
        adj_enable_item.SetValue(Config.autopos)
        adj_enable_item.Enable(False)
        adj_enable_item.Bind(wx.EVT_CHECKBOX, self.OnAdjEnable)

        x_pos_label = wx.StaticText(panel, label=u"x偏移:")
        x_pos_spin = wx.SpinCtrl(panel, -1, '', min=0, max=1000, initial=int(Config.posx), size=(50, -1))
        x_pos_spin.Bind(wx.EVT_SPINCTRL, self.OnSetPosX)
        x_pos_spin.Bind(wx.EVT_TEXT, self.OnSetPosX)

        y_pos_label = wx.StaticText(panel, label=u"y偏移:")
        y_pos_spin = wx.SpinCtrl(panel, -1, '', min=0, max=1000, initial=int(Config.posy), size=(50, -1) )
        y_pos_spin.Bind(wx.EVT_SPINCTRL, self.OnSetPosY)
        y_pos_spin.Bind(wx.EVT_TEXT, self.OnSetPosY)


        item_sizer.AddMany((
            (adj_enable_item, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 20),
            (x_pos_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5),
            (x_pos_spin, 0, wx.Center|wx.RIGHT, 15),
            (y_pos_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5),
            (y_pos_spin, 0, wx.Center|wx.RIGHT, 5) ,
        ))

        adj_sizer.Add(item_sizer, 1, wx.EXPAND )
        return  adj_sizer


    def viewer_sizer(self, main_panel):
        panel = main_panel
        mode_box = wx.RadioBox(panel, -1, u'显示模式', choices=[u'单设备模式', u'双设备模式'], name='mode')
        mode_box.Bind(wx.EVT_RADIOBOX, self.OnModeSelect)

        if Config.mode['mode'] == 'single':
            mode_box.SetSelection(0)
        else:
            mode_box.SetSelection(1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(mode_box, 0, wx.EXPAND)
        return sizer

    def aging_time_sizer(self, main_panel):
        panel = main_panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        aging_text = wx.StaticText(panel, label=u"老化时间:")
        aging_spin = wx.SpinCtrl(panel, -1, '', min=0, max=120, initial=int(Config.agetime) )
        sizer.Add(aging_text, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 10)
        sizer.Add(aging_spin, 0, wx.EXPAND)
        aging_spin.Bind(wx.EVT_SPINCTRL, self.OnAgingTimeSet)
        aging_spin.Bind(wx.EVT_TEXT, self.OnAgingTimeSet)

        return sizer

    def xinertai_sizer(self, main_panel):
        panel = main_panel
        sizer = wx.BoxSizer(wx.VERTICAL)
        # xinertai_text = wx.StaticText(panel, label=u"信儿泰程序路径:")
        xinertai_dirctl = filebrowse.DirBrowseButton(panel, labelText=u'信儿泰目录:', buttonText=u'浏览', toolTip=u'请选择信儿泰目录！', changeCallback=self.OnDirChanged)
        xinertai_dirctl.SetValue(Config.teledir)
        # sizer.Add(xinertai_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(xinertai_dirctl, 0, wx.EXPAND)
        return sizer

    def win_nums_sizer(self, main_panel):
        panel = main_panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        nums_text = wx.StaticText(panel, label=u"窗口数量:")
        nums_spin = wx.SpinCtrl(panel, -1, '', min=1, max=90, initial= int( Config.initwinnum ) )
        sizer.Add(nums_text, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 10)
        sizer.Add(nums_spin, 0, wx.EXPAND)
        nums_spin.Bind(wx.EVT_SPINCTRL, self.OnWinNumsSet)
        nums_spin.Bind(wx.EVT_TEXT, self.OnWinNumsSet)

        return sizer

    def OnAdjEnable(self, evt):
        Config.autopos = evt.IsChecked()
        msg = u'启用弹框定位' if Config.autopos else u'居中弹框'
        self.statusbar.SetStatusText(msg)

    def OnSetPosX(self, evt):
        Config.posx = evt.GetInt()
        self.statusbar.SetStatusText(u'x偏移：{}'.format(Config.posx))

    def OnSetPosY(self, evt):
        Config.posy = evt.GetInt()
        self.statusbar.SetStatusText(u'y偏移：{}'.format(Config.posy))

    def OnAgingTimeSet(self, evt):
        Config.agetime = evt.GetInt()
        self.statusbar.SetStatusText(u'老化时间：{}H'.format(evt.GetInt()))

    def OnWinNumsSet(self, evt):
        Config.initwinnum =  evt.GetInt()
        self.statusbar.SetStatusText(u'窗口数量：{}'.format(evt.GetInt()))

    def OnDirChanged(self, evt):

        Config.teledir = evt.GetString()
        Config.teleatt = os.path.join(Config.teledir, u'TeleATT.exe')
        Config.teleattcfg = os.path.join(Config.teledir, u'TeleATT.cfg')

        if os.path.exists(Config.teledir) and os.path.exists(Config.teleatt) and os.path.exists(Config.teleattcfg):
            self.statusbar.SetStatusText(u'路径：{}'.format(Config.teledir))
        else:
            self.statusbar.SetStatusText(u'信儿泰程序路径不正确')

    def OnModeSelect(self, evt):
        obj = evt.GetEventObject()
        obj_name = obj.GetName()
        self.statusbar.SetStatusText(evt.GetString())

        if obj_name == 'mode':
            if evt.GetSelection() == 0:
                Config.mode['mode'] = 'single'
            else:
                Config.mode['mode'] = 'double'
            self.statusbar.SetStatusText('重启后生效')

        if obj_name == 'viewer':
            main_frame = wx.Window.FindWindowByName('MainFrame')
            main_win = main_frame.main_window
            test_win = main_frame.test_window
            mes_win = main_frame.mes_window
            if evt.GetSelection() == 0:
                Config.mesarea_status = 'hide'
                main_win.Unsplit(mes_win)
            else:
                Config.mesarea_status = 'show'
                main_win.SplitVertically(mes_win, test_win)

    def OnProtocolSelect(self, evt):
        Config.protocol = evt.GetString().lower()
        self.statusbar.SetStatusText('{}'.format(evt.GetString()))

class VariablePanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.first_load = True
        self.dataDict = {}
        self.list = ListCtrl(self, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)
        self.list.InsertColumn(1, u'名称', width=180)
        self.list.InsertColumn(2, u'值')
        listmix.ColumnSorterMixin.__init__(self, self.list.GetColumnCount())

        self.refresh = wx.Button(self, label=u'刷新')
        self.refresh.Bind(wx.EVT_BUTTON, self.OnRefresh)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.refresh, 0, wx.EXPAND)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def FirstLoad(self, dataDict={}):
        self.dataDict = dataDict
        if self.first_load:
            self.itemDataMap = {}
            self.list.DeleteAllItems()
            for idx, key in enumerate(self.dataDict):
                self.itemDataMap[idx] = (key, self.dataDict[key])
                item = self.list.InsertItem(sys.maxint, key)
                self.list.SetItem(item, 1, str(self.dataDict[key]))
                self.list.SetItemData(item, idx)
            self.first_load = False

    def OnRefresh(self, evt):
        self.first_load = True
        self.FirstLoad(self.dataDict)

    def GetListCtrl(self):
        return self.list

class PanelText(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.first_load = True
        self.content = ''
        self.refresh = wx.Button(self, label=u'刷新')
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.refresh, 0, wx.EXPAND)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.refresh.Bind(wx.EVT_BUTTON, self.OnRefresh)

    def FirstLoad(self, content):
        self.content = content
        if self.first_load:
            self.text.Clear()
            self.text.AppendText(self.content)
            self.text.SetInsertionPoint(0)
            self.first_load = False

    def OnRefresh(self, evt):
        self.first_load = True
        self.FirstLoad(self.content)

class PDFPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.buttonpanel = pdfButtonPanel(self, wx.NewId(), wx.DefaultPosition, wx.DefaultSize, 0)
        self.viewer = pdfViewer(self, wx.NewId(), wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL | wx.VSCROLL | wx.SUNKEN_BORDER)
        self.buttonpanel.viewer = self.viewer
        self.viewer.buttonpanel = self.buttonpanel

        load_button = wx.Button(self, label=u'打开文件')
        load_button.Bind(wx.EVT_BUTTON, self.OnLoadButton)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(load_button, 0, wx.EXPAND)
        sizer.Add(self.buttonpanel, 0, wx.EXPAND)
        sizer.Add(self.viewer, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)

    def OnLoadButton(self, event):
        dlg = wx.FileDialog(self, wildcard="*.pdf")
        if dlg.ShowModal() == wx.ID_OK:
            wx.BeginBusyCursor()
            self.viewer.LoadFile(dlg.GetPath())
            wx.EndBusyCursor()
        dlg.Destroy()

class RePanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent )
        self.win = MultiSplitterWindow(self)
        # for tename, title, pos in (('whole_te', 'Whole Text', (0, 100)), ('part_te', 'Part Text', (0, 200)), ('re_te', 'Regular Expresion', (0, 250))):
        #     self.createTe(tename, title, pos)

        for tename, title, pos in (('whole_te', 'Whole Text', (0, 0)), ('re_te', 'Regular Expresion', (0, 200))):
            self.createTe(tename, title, pos)
        self.win.SetOrientation(wx.VERTICAL)

        self.info_bar = wx.InfoBar(self)
        file_button = wx.Button(self, label="Get File List")
        test_button = wx.Button(self, label='Execute')
        test_button.Bind(wx.EVT_BUTTON, self.OnReTest)
        file_button.Bind(wx.EVT_BUTTON, self.OnGetFile)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(file_button, 0, wx.EXPAND)
        sizer.Add(self.win, 1, wx.EXPAND)
        sizer.Add(test_button, 0, wx.EXPAND)
        sizer.Add(self.info_bar, 0, wx.EXPAND)
        self.SetSizer(sizer)

    def createTe(self, tename='', title='', pos=0):
        panel = wx.Panel(self.win)
        sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, label=title)
        setattr(self, tename, wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2))
        sizer.Add(getattr(self, tename), 1, wx.EXPAND)
        panel.SetSizer(sizer)
        self.win.AppendWindow(panel)
        self.win.SetSashPosition(pos[0], pos[1])

    def OnGetFile(self, evt):
        extern_WJTableName = Config.mes_attr['extern_WJTableName']
        extern_StationName = Config.mes_attr['extern_StationName']
        sql = "select filename  from DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}' and  w.createdate = (SELECT MAX(CREATEDATE) FROM \
                                  DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}')".format(
            extern_WJTableName, extern_StationName, extern_WJTableName, extern_StationName)
        filenams_list = Config.mes_db.fetchall(sql)
        for file_item in filenams_list:
            self.whole_te.AppendText(file_item[0] + '\n')

    def OnReTest(self, evt):
        whole_text = self.whole_te.GetValue()
        # part_text = self.part_te.GetValue()
        part_text = whole_text

        style = wx.TextAttr("RED", "WHITE")
        base_pos = whole_text.find(part_text)
        self.whole_te.SetStyle(0, len(whole_text) - 1, wx.TextAttr("BLACK", "WHITE"))

        for lineNo in range(self.re_te.GetNumberOfLines()):
            match_re_line = self.re_te.GetLineText(lineNo)
            match = re.search(match_re_line.strip(), part_text)
            if match and len(match.groups()):
                try:
                    match_relative_pos = match.span(1)
                    match_absolute_pos = (match_relative_pos[0] + base_pos, match_relative_pos[1] + base_pos)
                    self.whole_te.SetStyle(match_absolute_pos[0], match_absolute_pos[1], style)
                    self.whole_te.SetInsertionPoint(match_absolute_pos[0])
                except Exception as e:
                    pass

class MyHandler(FTPHandler):
    log_area = None
    def on_connect(self):
        if self.log_area:
            self.log_area.AppendText('----------{}----------\n'.format(self.banner))
            self.log_area.AppendText(u'<{}:{}> 连接\n'.format(self.remote_ip, self.remote_port))

    def on_disconnect(self):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 断开连接\n'.format(self.remote_ip, self.remote_port, self.username ))

    def on_login(self, username):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 登陆\n'.format(self.remote_ip, self.remote_port, self.username))

    def on_logout(self, username):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 退出\n'.format(self.remote_ip, self.remote_port, self.username ))

    def on_file_sent(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 下载文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file ))

    def on_file_received(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 上传文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file))

    def on_incomplete_file_sent(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 下载不完整文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file))

    def on_incomplete_file_received(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 上传不完整文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file))

class FTPSeverThread(threading.Thread):
    def __init__(self, share_dir, user, passwd, ip, handler):
        threading.Thread.__init__(self)
        self.share_dir = share_dir
        self.user = user
        self.passwd = passwd
        self.ip = ip
        self.handler = handler
        self.server = None

    def close(self):
        if self.server is not None:
            self.server.close_all()

    def run(self):
        authorizer = DummyAuthorizer()
        authorizer.add_user(self.user, self.passwd, self.share_dir, perm='elrw')
        authorizer.add_anonymous(self.share_dir)

        self.handler.authorizer = authorizer
        self.handler.banner = 'Welcome Raisecom'

        self.server = FTPServer((self.ip, 21), self.handler)
        self.server.serve_forever()

class FTPServerPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.CreateArea()

    def CreateArea(self):
        self.main_win = self
        self.ftp_thread = None
        self.CreateTopArea()
        self.CreateBottomArea()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.top_win, 0, wx.EXPAND)
        sizer.Add(self.bottom_win, 1, wx.EXPAND | wx.TOP, 5)
        self.main_win.SetSizer(sizer)

    def CreateTopArea(self):
        self.top_win = wx.Panel(self.main_win)
        self.file_btn = filebrowse.DirBrowseButton(self.top_win, labelText=u'①选择FTP目录:')

        header_text = wx.StaticText(self.top_win, label=u'②填写用户信息')
        user_st = wx.StaticText(self.top_win, label=u'用户:')
        self.user_tc = wx.TextCtrl(self.top_win, value='wrs')
        passwd_st = wx.StaticText(self.top_win, label=u'密码:')
        self.passws_tc = wx.TextCtrl(self.top_win, value=u'wrs')

        sizer_user = wx.BoxSizer(wx.HORIZONTAL)
        sizer_user.Add(header_text, 0, wx.EXPAND)
        sizer_user.Add(user_st, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_user.Add(self.user_tc, 0, wx.EXPAND)
        sizer_user.Add(passwd_st, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_user.Add(self.passws_tc, 0, wx.EXPAND)

        ip_st = wx.StaticText(self.top_win, label=u'③选择服务器IP:')
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice = wx.Choice(self.top_win, choices=choices)
        sizer_ip = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ip.Add(ip_st, 0, wx.EXPAND)
        sizer_ip.Add(self.ip_choice, 0, wx.EXPAND)

        create_btn = wx.Button(self.top_win, label=u'创建')
        create_btn.Bind(wx.EVT_BUTTON, self.CreateFTPServer, create_btn)

        stop_btn = wx.Button(self.top_win, label=u'停止')
        stop_btn.Bind(wx.EVT_BUTTON, self.StopFTPServer, stop_btn)

        sizer_thread = wx.BoxSizer(wx.HORIZONTAL)
        sizer_thread.Add(create_btn, 1, wx.EXPAND)
        sizer_thread.Add(stop_btn, 1, wx.EXPAND)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.file_btn, 0, wx.EXPAND)
        sizer_main.Add(sizer_user, 0, wx.EXPAND)
        sizer_main.Add(sizer_ip, 0, wx.EXPAND)
        sizer_main.Add(sizer_thread, 0, wx.EXPAND)
        self.top_win.SetSizer(sizer_main)

    def CreateBottomArea(self):
        self.bottom_win = wx.Panel(self.main_win)
        sizer = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_win, label=u'消息')
        self.log_area = wx.TextCtrl(self.bottom_win, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.log_area, 1, wx.EXPAND)
        self.bottom_win.SetSizer(sizer)

    def StopFTPServer(self, evt):
        if self.ftp_thread and self.ftp_thread.is_alive():
            self.ftp_thread.close()
            self.log_area.AppendText('断开连接\n')

    def CreateFTPServer(self, evt):
        share_dir = self.file_btn.GetValue()
        username = self.user_tc.GetValue()
        password = self.passws_tc.GetValue()
        ip = self.ip_choice.GetStringSelection()

        if share_dir and username and password and ip:
            handler = MyHandler
            handler.timeout = 9600
            handler.log_area = self.log_area
            self.StopFTPServer(None)
            self.ftp_thread = FTPSeverThread(share_dir, username, password, ip, handler)
            self.ftp_thread.start()
            self.log_area.AppendText('创建成功\n')

    def RefreshChoice(self):
        origin_selection = self.ip_choice.GetSelection()
        self.ip_choice.Clear()
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice.AppendItems(choices)
        self.ip_choice.SetSelection(origin_selection)

class TFTPSeverThread(threading.Thread):
    def __init__(self, share_dir, ip):
        threading.Thread.__init__(self)
        self.share_dir = share_dir
        self.ip = ip
        self.server = None
        self.create_success = None
        self.error_msg = None

    def close(self):
        if self.server is not None:
            self.server.stop(False)

    def run(self):
        try:
            self.server = tftpy.TftpServer(self.share_dir)
            self.server.listen()
        except socket.error as e:
            self.error_msg = e
            self.create_success = False

class TFTPServerPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.CreateArea()

    def CreateArea(self):
        self.main_win = self
        self.tftp_thread = None
        self.CreateTopArea()
        self.CreateBottomArea()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.top_win, 0, wx.EXPAND)
        sizer.Add(self.bottom_win, 1, wx.EXPAND | wx.TOP, 5)
        self.main_win.SetSizer(sizer)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def CreateTopArea(self):
        self.top_win = wx.Panel(self.main_win)
        self.file_btn = filebrowse.DirBrowseButton(self.top_win, labelText=u'①选择TFTP目录:')

        ip_st = wx.StaticText(self.top_win, label=u'③选择服务器IP:')
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice = wx.Choice(self.top_win, choices=choices)
        sizer_ip = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ip.Add(ip_st, 0, wx.EXPAND)
        sizer_ip.Add(self.ip_choice, 0, wx.EXPAND)

        create_btn = wx.Button(self.top_win, label=u'创建')
        create_btn.Bind(wx.EVT_BUTTON, self.CreateTFTPServer, create_btn)

        stop_btn = wx.Button(self.top_win, label=u'停止')
        stop_btn.Bind(wx.EVT_BUTTON, self.StopTFTPServer, stop_btn)

        sizer_thread = wx.BoxSizer(wx.HORIZONTAL)
        sizer_thread.Add(create_btn, 1, wx.EXPAND)
        sizer_thread.Add(stop_btn, 1, wx.EXPAND)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.file_btn, 0, wx.EXPAND)
        sizer_main.Add(sizer_ip, 0, wx.EXPAND)
        sizer_main.Add(sizer_thread, 0, wx.EXPAND)
        self.top_win.SetSizer(sizer_main)

    def CreateBottomArea(self):
        self.bottom_win = wx.Panel(self.main_win)
        sizer = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_win, label=u'消息')
        self.log_area = wx.TextCtrl(self.bottom_win, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.log_area, 1, wx.EXPAND)
        self.bottom_win.SetSizer(sizer)

    def StopTFTPServer(self, evt):
        if self.tftp_thread and self.tftp_thread.is_alive():
            self.tftp_thread.close()
            self.log_area.AppendText('断开连接\n')

    def CreateTFTPServer(self, evt):
        share_dir = self.file_btn.GetValue()
        ip = self.ip_choice.GetStringSelection()
        if share_dir and ip:
            self.StopTFTPServer(None)
            self.tftp_thread = TFTPSeverThread(share_dir, ip)
            self.tftp_thread.start()
            self.log_area.AppendText('创建成功\n')

    def OnIdle(self, evt):
        if self.tftp_thread:
            if len(self.tftp_thread.server.sessions):
                for key, value in self.tftp_thread.server.sessions.iteritems():
                    if type(value).__name__ == 'TftpContextServer':
                        self.log_area.AppendText('{} Receive {}Bytes\n'.format(key, value.getBlocksize()))

            if  self.tftp_thread.create_success is False:
                self.log_area.AppendText('创建失败\n')
                error_msg = self.tftp_thread.error_msg
                self.log_area.AppendText(error_msg+'\n')
                self.tftp_thread.create_success = None
                self.tftp_thread.error_msg = None

    def RefreshChoice(self):
        origin_selection = self.ip_choice.GetSelection()
        self.ip_choice.Clear()
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice.AppendItems(choices)
        self.ip_choice.SetSelection(origin_selection)

#popupwindow to show listctrl(report mode) content
class PopupFrame(wx.Frame):
    def __init__(self, parent, id, title, pos , content, style=wx.DEFAULT_FRAME_STYLE, size=wx.DefaultSize):
        wx.Frame.__init__(self, parent, id , title, pos, style=style, size=size)
        self.SetIcon(wx.Icon(Config.logofile))
        panel = wx.Panel(self)
        tc = wx.TextCtrl(panel, -1, style=wx.TE_MULTILINE | wx.TE_RICH2|wx.TE_NOHIDESEL)
        tc.SetValue(ftfy.fix_text(unicode(content)))
        # tc.SetValue( ftfy.fix_text( unicode(content, errors='ignore') ))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tc, 1, wx.EXPAND)
        panel.SetSizer(sizer)

class SearchPanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.panel = self
        sz = (-1, 25)
        self.workorder_st = wx.StaticText(self.panel, -1, u'工单号:', style=wx.ALIGN_BOTTOM, size=sz)
        self.workorder_tc = wx.TextCtrl(self.panel, -1, '', size=sz)

        self.sn_st = wx.StaticText(self.panel, -1, 'SN:', style=wx.ALIGN_BOTTOM, size=sz)
        self.sn_tc = wx.TextCtrl(self.panel, -1, '', size=(210, -1))

        time_st = wx.StaticText(self.panel, -1, '时间:', style=wx.ALIGN_LEFT, size=sz)
        self.starttime_picker = wx.adv.DatePickerCtrl(self.panel)
        dash_st = wx.StaticText(self.panel, -1, '-', style=wx.ALIGN_BOTTOM, size=sz)
        self.endtime_picker = wx.adv.DatePickerCtrl(self.panel)
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time.Add(time_st)
        sizer_time.Add(self.starttime_picker, 0, wx.LEFT, 5)
        sizer_time.Add(dash_st, 0, wx.LEFT, 5)
        sizer_time.Add(self.endtime_picker, 0, wx.LEFT, 5)

        operator_st = wx.StaticText(self.panel, -1, '操作员:', style=wx.ALIGN_BOTTOM, size=sz)
        self.operator_tc = wx.TextCtrl(self.panel, -1, '')

        productname_st = wx.StaticText(self.panel, -1, '产品名称:', style=wx.ALIGN_BOTTOM, size=sz)
        self.productname_tc = wx.TextCtrl(self.panel, -1, '')

        result_st = wx.StaticText(self.panel, -1, '结果:', style=wx.ALIGN_BOTTOM, size=sz)
        self.result_choice = wx.Choice(self.panel, choices=['', 'PASS', 'FAIL'])

        self.export_bn = wx.Button(self.panel, -1, u'导出', size=sz)
        self.search_bn = wx.Button(self.panel, -1, 'Search', size=sz)
        self.export_bn.Bind(wx.EVT_BUTTON, self.OnExportData)

        suite_in, suite_out = 5, 10
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.workorder_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.workorder_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(self.sn_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.sn_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)

        hsizer.Add(sizer_time, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(operator_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.operator_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(productname_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.productname_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(result_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.result_choice, 0, wx.EXPAND | wx.RIGHT, suite_out)

        hsizer.AddStretchSpacer()
        hsizer.Add(self.export_bn, 0, wx.RIGHT|wx.EXPAND, 5)
        hsizer.Add(self.search_bn, 0, wx.EXPAND)

        self.list_lc = ListCtrl(self.panel, -1, style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_SORT_ASCENDING)
        columns = [u'IDX', u'ID', u'工序' , u'线体' , u'SN', u'MAC', u'结果', u'起始时间', u'结束时间', u'测试时间', u'操作员', u'工单号', u'BOM编码', u'产品名称', u'产品版本', u'批次号',
                   u'串口日志', u'测试项日志', u'物料代码', u'备注']
        for col, text in enumerate(columns):
            self.list_lc.InsertColumn(col, text)
        listmix.ColumnSorterMixin.__init__(self, self.list_lc.GetColumnCount())
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM)
        vsizer.Add(self.list_lc, 1, wx.EXPAND)
        self.panel.SetSizer(vsizer)
        self.list_lc.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_BUTTON, self.OnSearch, self.search_bn)

    def OnExportData(self, evt):
        start_datetime = self.starttime_picker.GetValue()
        end_datetime = self.endtime_picker.GetValue()
        if self.productname_tc.GetValue():
            defaultFileName = '{} {}-{}'.format(self.productname_tc.GetValue(), start_datetime.Format("%Y%m%d"), end_datetime.Format("%Y%m%d"))
        else:
            defaultFileName = '{}-{}'.format(start_datetime.Format("%Y%m%d"), end_datetime.Format("%Y%m%d"))
        dlg = wx.FileDialog(self, message="保存", defaultDir='',defaultFile=defaultFileName,
                            wildcard=u"Excel97 文件 (*.xls)|*.xls|Excel2010 文件 (*.xlsx)|*.xlsx|csv 文件 (*.csv)|*.csv", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT|wx.FD_CHANGE_DIR)
        df = pd.DataFrame(self.itemDataMap)
        df = df.transpose()
        df = df.fillna(value='')
        if dlg.ShowModal() ==  wx.ID_OK:
            columns = []
            for col_id in self.list_lc.GetColumnsOrder():
                colobj = self.list_lc.GetColumn(col_id)
                columns.append(colobj.GetText())
            df.columns = columns
            df = df.drop(columns=[u'IDX', u'ID', u'串口日志', u'测试项日志'])
            if os.path.splitext(dlg.GetFilename())[1] == '.csv':
                df.to_csv(dlg.GetPath(), encoding='gbk')
            else:
                df.to_excel(dlg.GetPath(), sheet_name=defaultFileName)

    def OnSearch(self, evt):
        # sql = "select sn, segment1 ,result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, logserial, logprocess, segment2 ,description from sn_table"
        # sql = "select id, sn, segment1 ,result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, segment2 ,description from sn_table"
        sql = "select @rownr:=@rownr+1 as idx, id, segment3, segment4, sn, segment1 ,result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, '', '' ,segment2 ,description from sn_table "
        sn = self.sn_tc.GetValue().strip()
        order = self.workorder_tc.GetValue().strip()
        starttime = self.starttime_picker.GetValue().FormatISODate()
        endtime = self.endtime_picker.GetValue().FormatISODate()
        operator = self.operator_tc.GetValue().strip()
        productname = self.productname_tc.GetValue().strip()
        result = self.result_choice.GetString(self.result_choice.GetSelection())

        sql += "where sn like \"%{}%\" and ifnull(workorder, '') like \"%{}%\" and operator like \"%{}%\" " \
               "and productname like \"%{}%\"  and result like \"%{}%\"  and starttime >= \"{}\" and endtime <= date_add(\"{}\", interval 1 day) ".format(
            sn, order, operator, productname, result, starttime, endtime)
        self.list_lc.DeleteAllItems()
        Config.db.execute("set @rownr=0")
        sql_value = Config.db.fetchall(sql)
        self.itemDataMap = {}

        for row, rowdata in enumerate(sql_value):
            self.itemDataMap[row] = rowdata

        for key, rowdata in self.itemDataMap.items():
            index = self.list_lc.InsertItem(sys.maxint, str(key))
            self.list_lc.SetItemData(index, key)
            for col in range(self.list_lc.GetColumnCount()):
                self.list_lc.SetItem(index, col, mes_value(rowdata[col]))

    def OnLeftDClick(self, evt):
        item, where, subitem = self.list_lc.HitTestSubItem(evt.GetPosition())
        data = self.itemDataMap[self.list_lc.GetItemData(item)]
        pos = self.list_lc.ClientToScreen(evt.GetPosition())
        col_info = self.list_lc.GetColumn(subitem)
        title = data[4] + ' -- ' + col_info.GetText()

        if col_info.GetText() == '串口日志':
            sql = "select logserial from sn_table where id={}".format(data[1])
            sql_value = Config.db.fetchone(sql)
            pop_content = sql_value[0]
        elif col_info.GetText() == '测试项日志':
            sql = "select logprocess from sn_table where id={}".format(data[1])
            sql_value = Config.db.fetchone(sql)
            pop_content = sql_value[0]
        else:
            pop_content = data[subitem]
        popup_win = PopupFrame(self, -1, title, pos, pop_content, size=(500, -1))
        popup_win.Show()

    def GetListCtrl(self):
        return self.list_lc

class BugFrame( wx.Frame):
    def __init__(self, parent, title='', size=wx.DefaultSize):
        wx.Frame.__init__(self, parent=parent, title=title, size=size, name='BugFrame')
        self.SetIcon(wx.Icon(Config.logofile))
        self.book = wx.Notebook(self, -1, style=wx.NB_MULTILINE)

        self.book.InsertPage(0, PanelText(self.book), '程序异常信息')
        self.book.InsertPage(1, PanelText(self.book), '脚本运行信息')
        self.book.InsertPage(2, VariablePanel(self.book), '脚本运行变量')
        self.book.InsertPage(3, RePanel(self.book), '表达式验证')

        self.book.InsertPage(4, FTPServerPanel(self.book), 'FTP Server')
        self.book.InsertPage(5, TFTPServerPanel(self.book), 'TFTP Server')
        self.book.InsertPage(6, SearchPanel(self.book), '数据库查询')
        self.book.InsertPage(7, PDFPanel(self.book), 'PDF阅读器')
        self.book.InsertPage(8, shell.Shell(self.book), 'Shell')

        self.book.Bind(wx.EVT_BOOKCTRL_PAGE_CHANGED, self.OnChanged)
        self.book.SetPadding((5, 0))
        self.book.SetSelection(0)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        page = self.book.GetPage(4)
        page.StopFTPServer(None)

        page = self.book.GetPage(5)
        page.StopTFTPServer(None)

        self.Destroy()

    def OnChanged(self, evt):
        pageNumber = evt.GetSelection()
        if pageNumber == 0:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad(Config.debughandler.getvalue())
        elif pageNumber == 1:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad(Config.processhandler.getvalue())
        elif pageNumber == 2:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad(Config.vars)
        elif pageNumber in [4, 5]:
            page = self.book.GetPage(pageNumber)
            page.RefreshChoice()

class DownLoadSopWindow(wx.Frame):
    def __init__(self, parent, title, size=wx.DefaultSize):
        wx.Frame.__init__(self, parent = parent, title = title, size=size)
        self.SetIcon(wx.Icon(Config.logofile))
        extern_SubAttemperCode = Config.mes_attr['extern_SubAttemperCode']
        extern_stritemcode = Config.mes_attr['extern_stritemcode']
        extern_StationName = Config.mes_attr['extern_StationName']

        self.panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.infobar = wx.InfoBar(self.panel)
        sql_field = ','.join(['CODE','ID','TESTPOSITIONNAME','TESTPOSITIONCODE','FLAG','FILENAME','FILEITEMTYPE',
                              'FILEPATH','FILEDESCRIBE','DESCRIBE','inputman','INPUTDATE','ITEMCODE','ITEMTYPE','ITEMVERSION','ITEMDESCRIBE','ITEMLINE'])
        columns = [u'单据号',  u'序号', u'工序', u'工序代码', u'SOP编码', u'文件名称', u'版本类型',  u'文件路径', u'文件说明', u'备注', u'修改人', u'录入日期',
                   u'产品编码', u'产品型号', u'产品版本', u'产品名称', u'产品系列']

        sql = "select m.mpkbeginbarcode  from DMSNEW.mtl_sub_attemper  m where m.sub_attempter_code ='{}' ".format(extern_SubAttemperCode)
        sql_value = Config.mes_db.fetchone(sql)
        if sql_value[0] is None:
            sql = "select {} from DMSNEW.view_TAB_SOPSUBBOOK where ITEMCODE='{}'  and TESTPOSITIONNAME='{}' order by code,id ".format(sql_field, extern_stritemcode, extern_StationName)
        else:
            sql = "select {} from DMSNEW.view_TAB_SOPSUBBOOK where ITEMCODE='{}' and flag in " \
                  "(select column_value from table(f_split('{}',',')) where column_value is not null ) " \
                  "order by code,id ".format(sql_field, extern_stritemcode, sql_value[0])

        self.data  = Config.mes_db.fetchall(sql)
        self.list = ListCtrl(self.panel, -1, style=wx.LC_REPORT)

        for col, label in enumerate(columns):
            self.list.InsertColumn(col, label)

        for row, value in enumerate(self.data):
            self.list.InsertItem(row, '')
            for col in range(len(columns)):
                if value[col] != None:
                    self.list.SetItem(row, col, unicode(value[col]))
                else:
                    self.list.SetItem(row, col, '')

        for col in range(len(columns)):
            self.list.SetColumnWidth(col, wx.LIST_AUTOSIZE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.infobar, wx.SizerFlags().Expand())
        sizer.Add(self.list, 1, wx.GROW)
        self.panel.SetSizer(sizer)
        self.list.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        # self.statusbar = self.CreateStatusBar(style=wx.STB_SIZEGRIP)

    def OnRightDown(self, evt):
        menu = wx.Menu()
        downloaditem = menu.Append(-1, u'下载')
        self.Bind(wx.EVT_MENU, self.OnDownLoadFile, downloaditem)
        self.PopupMenu(menu)

    def OnDownLoadFile(self, evt):
        sel_data = self.data[self.list.GetFocusedItem()]
        sql = " SELECT  ftpaddress,ftpport,ftpuser,ftppass,ftppath,segment2 from dmsnew.TAB_FTPSENDLOADINFOR where ftptype ='SOP' and segment1 ='下载'  "
        sql_value = Config.mes_db.fetchone(sql)
        ftpaddress = mes_value(sql_value[0] )
        ftpport = mes_value(sql_value[1])
        ftpuser = mes_value(sql_value[2])
        ftppass = mes_value(sql_value[3])
        ftppath = mes_value(sql_value[4])
        ftppathshare = mes_value(sql_value[5])

        filename, filepath = sel_data[5], sel_data[7]
        if filename == '':
            self.infobar.ShowMessage(u'SOP名称为空，不能查阅作业指导书')
            return

        if filepath == '':
            self.infobar.ShowMessage(u'SOP文件路径为空，不能查阅作业指导书')
            return

        ftp = ftputil.FTPHost(ftpaddress, ftpuser, ftppass)
        if filepath != '':
            soppath = os.path.join('\\',ftppathshare, filepath, filename)
        else:
            soppath = os.path.join('\\',ftppathshare, filename)

        soppath = os.path.normpath(soppath)
        dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=wx.GetUserName(), defaultFile=filename,
                            style=wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT)
        dlg.SetWildcard("All files (*.*)|*.*|" + "Text file (*.txt)|*.txt|" + "Binary file (*.bin)|*.bin|")

        if dlg.ShowModal() == wx.ID_OK:
            try:
                ftp.download(soppath.encode('gb2312'), dlg.GetPath())
            except ftputil.error.FTPIOError as e:
                self.infobar.ShowMessage(u'{} 下载失败'.format(filename), flags=wx.ICON_ERROR)
            else:
                self.infobar.ShowMessage(u'{} 下载成功'.format(filename))
            finally:
                ftp.close()

class DownLoadWindow(wx.Frame):
    def __init__(self, parent, title, size=wx.DefaultSize):
        wx.Frame.__init__(self, parent=parent, title=title, size=size)
        self.SetIcon(wx.Icon(Config.logofile))
        extern_WJTableName = Config.mes_attr['extern_WJTableName']
        extern_StationName = Config.mes_attr['extern_StationName']

        self.panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.infobar = wx.InfoBar(self.panel)
        sql_field = ','.join(["workjob_code", "code", "testposition"   , "softcode" , "softname", "softtype",
                "softver"  ,"filename" , "filepath", "item_describe", "item_version", "item_type", "item_code" ])
        columns = [u'任务单号',  u'单据号', u'工序', u'软件编码', u'软件名称', u'软件类型', u'软件版本',
                   u'文件名称', u'文件路径', u'产品名称', u'产品版本', u'产品类型', u'产品编码']
        sql = "select {}  from DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}' and  w.createdate = (SELECT MAX(CREATEDATE) FROM \
              DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}')".format(sql_field, extern_WJTableName, extern_StationName,extern_WJTableName, extern_StationName)

        self.data  = Config.mes_db.fetchall(sql)
        self.list = ListCtrl(self.panel, -1, style=wx.LC_REPORT)

        for col, label in enumerate(columns):
            self.list.InsertColumn(col, label)

        for row, value in enumerate(self.data):
            self.list.InsertItem(row, '')
            for col in range(len(columns)):
                if value[col] != None:
                    self.list.SetItem(row, col, unicode(value[col]))
                else:
                    self.list.SetItem(row, col, '')

        for col in range(len(columns)):
            self.list.SetColumnWidth(col, wx.LIST_AUTOSIZE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.infobar, wx.SizerFlags().Expand())
        sizer.Add(self.list, 1, wx.GROW)
        self.panel.SetSizer(sizer)
        self.list.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        # self.statusbar = self.CreateStatusBar(style=wx.STB_SIZEGRIP)

    def OnRightDown(self, evt):
        menu = wx.Menu()
        downloaditem = menu.Append(-1, u'下载')
        self.Bind(wx.EVT_MENU, self.OnDownLoadFile, downloaditem)
        self.PopupMenu(menu)

    def OnDownLoadFile(self, evt):
        sel_data = self.data[self.list.GetFocusedItem()]
        sql = "select ftpaddress,ftpport,ftpuser,ftppass,ftppath,segment2 from DMSNEW.TAB_FTPSENDLOADINFOR where ftptype ='SOFT' and segment1 ='下载'  "
        sql_value = Config.mes_db.fetchone(sql)
        ftpaddress = mes_value(sql_value[0] )
        ftpport = mes_value(sql_value[1])
        ftpuser = mes_value(sql_value[2])
        ftppass = mes_value(sql_value[3])
        ftppath = mes_value(sql_value[4])

        ftp = ftputil.FTPHost(ftpaddress, ftpuser, ftppass)
        # basedir  = '/{}'.format(ftppath) if sel_data[8] == None  else sel_data[8]
        basedir = '/{}/{}'.format(ftppath, sel_data[8])
        filename = sel_data[7]
        filepath = os.path.normpath( os.path.join(basedir, filename) )

        dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=wx.GetUserName(), defaultFile=filename,
                            style=wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT)
        dlg.SetWildcard("All files (*.*)|*.*|" + "Text file (*.txt)|*.txt|" + "Binary file (*.bin)|*.bin|")

        if dlg.ShowModal() == wx.ID_OK:
            remote_filepath = filepath.decode('utf-8').encode('gbk')
            try:
                ftp.download(remote_filepath, dlg.GetPath())
            except ftputil.error.FTPIOError as e:
                self.infobar.ShowMessage(u'文件不存在, 软件下载失败', flags=wx.ICON_ERROR)
            else:
                self.infobar.ShowMessage(u'软件下载成功')
            finally:
                ftp.close()

#Login Window
class LoginDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title=u'登陆:' )
        self.SetIcon(wx.Icon(Config.logofile))
        self.job_number_ST = wx.StaticText(self, -1, u'MES账号:')
        self.job_number_TC = wx.TextCtrl(self, -1, Config.wn)

        job_sizer = wx.BoxSizer(wx.HORIZONTAL)
        job_sizer.Add(self.job_number_ST, 0, wx.GROW|wx.CENTER)
        job_sizer.Add(self.job_number_TC, 1, wx.GROW|wx.CENTER)

        self.password_ST = wx.StaticText(self, -1, u'MES密码:')
        self.password_TC = wx.TextCtrl(self, -1, '', style=wx.TE_PASSWORD)
        self.password_TC.SetFocus()

        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_sizer.Add(self.password_ST, 0, wx.GROW | wx.CENTER)
        password_sizer.Add(self.password_TC, 1, wx.GROW | wx.CENTER)

        # ok, cancel button
        okay = wx.Button(self, wx.ID_OK)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL)
        btsz = wx.StdDialogButtonSizer()
        btsz.AddButton(okay)
        btsz.AddButton(cancel)
        btsz.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(job_sizer, 0, wx.GROW)
        sizer.Add(password_sizer, 0, wx.GROW)
        sizer.Add((250, 20), 0, wx.GROW)
        sizer.Add(btsz, 0, wx.GROW)
        self.SetSizerAndFit(sizer)
        self.Center()


    def SetWN(self):
        while True:
            if self.ShowModal() == wx.ID_OK:
                job_number = self.job_number_TC.GetValue().strip()
                password = self.password_TC.GetValue()
                sql = "select dispname, passwords, userid from dmsnew.rs_user1 where userid='{}'".format(job_number)
                sql_value = Config.mes_db.fetchone(sql)

                if sql_value is None:
                    self.SetTitle('登陆:无效账号')
                else:
                    mes_uname, mes_password, mes_uid = sql_value[0], sql_value[1], sql_value[2]
                    if mes_password == password:
                        ret_status = True
                        Config.wn, Config.wnname = mes_uid, mes_uname

                        sql = "select rolesn from dmsnew.rs_role where rolesn in (select rolesn from " \
                              " DMSNEW.RS_USERROLE where usersn in (select usersn from DMSNEW.RS_USER1 where userid='{}')  )".format(mes_uid)
                        sql_value = Config.mes_db.fetchall(sql)

                        if not sql_value :
                            Config.right['test_right'] = False
                            Config.right['repaire_right'] = False
                            Config.right['workorder_right'] = False
                        else:
                            for rolesn in sql_value:
                                if rolesn[0] in [1, 3]:
                                    Config.right['test_right'] = True
                                    Config.right['repaire_right'] = True
                                    Config.right['workorder_right'] = True
                                    break
                                elif rolesn[0] in [24]:
                                    Config.right['test_right'] = False
                                    Config.right['repaire_right'] = True
                                    Config.right['workorder_right'] = False
                                    break
                        break
                    else:
                        self.SetTitle('登陆:密码错误')
            else:
                ret_status = False
                break
        self.Destroy()
        return ret_status

class WorkJobInfoDialog(wx.Dialog):
    def __init__(self, parent):
        super(self.__class__, self).__init__(parent, title=u'工单信息')
        self.SetIcon(wx.Icon(Config.logofile))
        size_ST = (60, -1)
        #工序输入
        # station_choice = ['SZ301(测试)', 'SZ016(半成品测试)']
        station_choice = ['SZ301', 'SZ016']
        self.stationST = wx.StaticText(self, -1, u'工序:', size=size_ST)
        self.station_choice = wx.Choice(self, choices=station_choice)
        self.station_choice.SetSelection(self._index(station_choice,  Config.mes_attr['extern_StationCode']))

        #线体选择
        # line_chocie = ['FA(A线)', 'FB(B线)', 'FC(C线)', 'FCS(F测试)', 'FD(D线)', 'FE(测试)', 'D01(D01)', 'SH01(售后)']
        line_choice = self._GetLineChoices()
        self.lineST = wx.StaticText(self, -1, u'线体:', size=size_ST)
        self.line_choice = wx.Choice(self, choices=line_choice)
        self.line_choice.SetSelection(self._index(line_choice, Config.mes_attr['extern_SubLineCode']))

        #工单输入
        self.wjtST = wx.StaticText(self, -1, u'工单号:', size=size_ST)
        self.wjtTC = wx.TextCtrl(self, -1,  Config.mes_attr['extern_WJTableName'])

        #投入人数
        self.workers_ST = wx.StaticText(self, -1, u'投入人数:', size=size_ST)
        self.workers_SP = wx.SpinCtrl(self, -1, initial=Config.mes_attr['op_workers'], min=1, max=99)

        sizer_station = wx.BoxSizer(wx.HORIZONTAL)
        sizer_station.Add(self.stationST, 0, wx.GROW | wx.CENTER)
        sizer_station.Add(self.station_choice, 1, wx.GROW | wx.CENTER)

        sizer_line = wx.BoxSizer(wx.HORIZONTAL)
        sizer_line.Add(self.lineST, 0, wx.GROW | wx.CENTER)
        sizer_line.Add(self.line_choice, 1, wx.GROW | wx.CENTER)

        sizer_wjt = wx.BoxSizer(wx.HORIZONTAL)
        sizer_wjt.Add(self.wjtST, 0, wx.GROW | wx.CENTER)
        sizer_wjt.Add(self.wjtTC, 1, wx.GROW | wx.CENTER)

        sizer_workers = wx.BoxSizer(wx.HORIZONTAL)
        sizer_workers.Add(self.workers_ST, 0, wx.GROW | wx.CENTER)
        sizer_workers.Add(self.workers_SP, 1, wx.GROW | wx.CENTER)

        # ok, cancel button
        okay = wx.Button(self, wx.ID_OK)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL)
        btsz = wx.StdDialogButtonSizer()
        btsz.AddButton(okay)
        btsz.AddButton(cancel)
        btsz.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer_station, 0, wx.GROW)
        sizer.Add(sizer_line, 0, wx.GROW)
        sizer.Add(sizer_workers, 0, wx.GROW)
        sizer.Add(sizer_wjt, 0, wx.GROW)
        sizer.Add((250, 20), 0, wx.GROW)
        sizer.Add(btsz, 0, wx.GROW)
        self.SetSizerAndFit(sizer)
        self.Center()

    def _index(self, choice, value):
        for v in choice:
            if value in v:
                return choice.index(v)
        return -1

    def _GetLineChoices(self):
        sql = "select distinct linecode,line from dmsnew.workproduce"
        value = Config.mes_db.fetchall(sql)

        line_choice = []
        for line_code, line_name in value:
            line_choice.append(line_code)
        return line_choice

    def GetWorkJobInfo(self):
        if self.ShowModal() == wx.ID_OK:
            Config.mes_attr['extern_StationCode'] = self.station_choice.GetStringSelection()
            Config.mes_attr['extern_SubLineCode'] = self.line_choice.GetStringSelection()
            Config.mes_attr['extern_WJTableName'] = self.wjtTC.GetValue().strip()
            Config.mes_attr['op_workers'] = self.workers_SP.GetValue()
            self.Destroy()
            return True
        self.Destroy()
        return False

class ReadyListCtrl(ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.BORDER_NONE)
        self.itemDataMap = {}
        column_fields = [(u'NO', 35), (u'SN', 210)]
        for idx, header in enumerate(column_fields):
            self.InsertColumn(idx, header[0], width=header[-1])
            # self.RefreshData()
        listmix.ColumnSorterMixin.__init__(self, self.GetColumnCount())

    def PopulateData(self):
        for idx, data  in enumerate((tool.get_available_sn())):
            self.itemDataMap[idx] = (idx, data)

    def ShowData(self):
        for key, data in self.itemDataMap.items():
            index = self.InsertItem(self.GetItemCount(), '')
            for col in range(self.GetColumnCount()):
                self.SetItem(index, col , str(data[col]))
            self.SetItemData(index, key)

    def RefreshData(self):
        try:
            self.DeleteAllItems()
            self.itemDataMap = {}
            self.PopulateData()
            self.ShowData()
        except Exception as e:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    def GetListCtrl(self):
        return self


class FinishListCtrl(ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.BORDER_NONE)
        self.itemDataMap = {}
        column_fields = [(u'NO', 35 ), (u'工序号', 50 ), (u'条码', 210 ), (u'工序', 40),
                         (u'线体', 40), (u'不良现象', 60), (u'电性/外观', 70 ), (u'扫描时间', 100)]
        for idx, header in enumerate(column_fields):
            self.InsertColumn(idx, header[0], width=header[-1])
            # self.RefreshData()
        listmix.ColumnSorterMixin.__init__(self, self.GetColumnCount())

    def PopulateData(self):
        extern_SubAttemperCode = Config.mes_attr['extern_SubAttemperCode']
        extern_AttempterCode = Config.mes_attr['extern_AttempterCode']
        sql = "select rownum no,subid,barcode,testposition,line_code2,qulity_plobolem,REPAIR,scan_time from dmsnew.{} where subattemper_code='{}' " \
              "order by scan_time desc, barcode".format( extern_AttempterCode, extern_SubAttemperCode)
        sql_value = Config.mes_db.fetchall(sql)
        if sql_value:
            for idx, data in enumerate(sql_value):
                self.itemDataMap[idx] = data

    def ShowData(self):
        for key, data in self.itemDataMap.items():
            index = self.InsertItem(self.GetItemCount(), key)
            for col in range(self.GetColumnCount()):
                self.SetItem(index, col, str(data[col]) if data[col] else '' )
            if data[5]: self.SetItemTextColour(index, wx.RED)
            self.SetItemData(index, key)

    def RefreshData(self):
        try:
            self.DeleteAllItems()
            self.itemDataMap = {}
            self.PopulateData()
            self.ShowData()
        except Exception as e:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    def GetListCtrl(self):
        return self