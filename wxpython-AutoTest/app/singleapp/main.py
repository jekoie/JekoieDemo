# coding=utf-8
from __future__ import division
from ..common import common
from ..common import feature
from ..common import communicate
from ..oracle import cx_Oracle
from .product import Product
from .product import EVT_THREAD_DIALOG
from .product import EVT_THREAD_DEATH
import pandas as pd
import wx.adv
import functools
import math
import wx.lib.dialogs
from wx.lib.pubsub import pub
import platform
import arrow
import Queue
import wx.lib.agw.ultimatelistctrl as ULC
import wx.lib.mixins.inspection as wit
import pathlib
import wx
import wx.adv
import re
import os
import sys
import wx.lib.dialogs
import serial
import serial.serialutil
import traceback
import  wx.lib.mixins.listctrl  as  listmix
import threading
import socket
import base64
import MySQLdb
import time
from lxml import etree
from wx.lib.splitter import MultiSplitterWindow
from .. import __version__, __appname__, __author__
############################单串口版##############################
reload(sys)
sys.setdefaultencoding('utf-8')
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'

#colour
COLOUR_RED = wx.Colour(249, 0, 0)
COLOUR_GREEN = wx.Colour(0, 249, 0)
COLOUR_YELLOW = wx.Colour(239, 249, 49)
COLOUR_WHITE = wx.Colour(255, 255, 255)
COLOUR_BLACK = wx.Colour(0, 0, 0)
COLOUR_GRAY = wx.Colour(127, 127, 127)
COLOUR_AQUA = wx.Colour(32,178,170)

#topic string
TOPIC_CLOSE_SERIAL = 'TOPIC_CLOSE_SERIAL'
TOPIC_START_TEST = 'TOPIC_START_TEST'
TOPIC_PORT_SET = 'TOPIC_PORT_SET'
TOPIC_STOP_TEST = 'TOPIC_STOP_TEST'
TOPIC_DISSCONECT_SERIAL = 'TOPIC_DISSCONECT_SERIAL'
TOPIC_RECONNECT_SERIAL = 'TOPIC_RECONNECT_SERIAL'
TOPIC_PAUSE_TEST = 'TOPIC_PAUSE_TEST'
TOPIC_RESUME_TEST = 'TOPIC_RESUME_TEST'
TOPIC_TRANSFER_WIN = 'TOPIC_TRANSFER_WIN'
TOPIC_DISABLE_WIN = 'TOPIC_DISABLE_WIN'
TOPIC_APPCONFIG_RECEIVE = 'TOPIC_APPCONFIG_RECEIVE'
TOPIC_APPCONFIG_TRANSFER = 'TOPIC_APPCONFIG_TRANSFER'
TOPIC_MESDB_CHANGE = 'TOPIC_MESDB_CHANGE'
TOPIC_WORKTABLE_LOAD = 'TOPIC_WORKTABLE_LOAD'

#linefeed style
LINEFEED_NONE = ''
LINEFEED_LF = '\n'
LINEFEED_CR = '\r'
LINEFEED_CRLF = '\r\n'

APPCONFIG = {}
#窗口页UI， 命令输入， 日志显示，运行过程信息显示
class DevicePage(wx.Panel):
    pool = {}
    def __init__(self, parent, name='', win_idx=None):
        wx.Panel.__init__(self, parent)
        #page index number and linefeed style
        self.win_idx = win_idx
        self.linefeed = LINEFEED_CR
        #widget size
        wsz = [103, -1]
        #设置窗口名称
        self.name = name
        #DevicePage 窗体对象
        self.dev_win = None
        #所测试的产品（线程对象）
        self.product = None
        #所连接的设备对象
        self.dev = None
        #thread data queue
        self.thread_data_queue = Queue.Queue(1)
        self._connect_deive(APPCONFIG['protocol'])
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
        self.message_win = feature.MessageWindow(self)
        mid_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mid_sizer.Add(self.message_win, 1, wx.GROW)
        self.log_area = self.message_win.log_area
        #########################################mid area##############################################################

        #########################################botton area############################################################
        #bottom sizer include clear button that place the bottom of the sizer
        self.bottom_sizer = bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_item_size = (-1, 25)
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
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        #receive sub thread event and pop up a dialog
        self.Bind(EVT_THREAD_DIALOG, self.OnThreadDialog)
        self.Bind(EVT_THREAD_DEATH, self.OnThreadDeath)

        #接收 测试开始  主题
        pub.subscribe(self.OnUnitTest, TOPIC_START_TEST)
        # 接收 端口设置改变  主题（DeviceWindow设置改变时，同步设置到设备）
        pub.subscribe(self.OnPortSet, TOPIC_PORT_SET)
        #接收 测试case终止  主题
        pub.subscribe(self.OnStop, TOPIC_STOP_TEST)
        #接收 DeiveWindow对象  主题
        pub.subscribe(self.OnGetWin, TOPIC_TRANSFER_WIN)
        #接收 串口断开连接通信  主题
        pub.subscribe(self.OnDissconect, TOPIC_DISSCONECT_SERIAL)
        #接收 重新连接串口 主题
        pub.subscribe(self.OnReconnct, TOPIC_RECONNECT_SERIAL)
        #接收 MES数据库改变 主题
        pub.subscribe(self.OnMesdbChange, TOPIC_MESDB_CHANGE)

    def __del__(self):
        if self.dev.alive:self.dev.close()

    #分配设备对象并连接
    def _connect_deive(self, protocol):
        if protocol == 'serial':
            self.dev = communicate.communicate_factory(type=protocol, port=self.name)
            setting_value = common.get_serial_setting_by_name(APPCONFIG['setting_file'], self.name)
            self.dev.apply_settings(**setting_value)
            self.dev.connect()
        elif protocol == 'telnet':
            self.dev = communicate.communicate_factory(type=protocol )

    def OnMesdbChange(self, msg):
        self.tip_text.SetLabelText(msg)
        self.bottom_sizer.Layout()

    def OnThreadDeath(self, evt):
        APPCONFIG['var_im'].clear()
        APPCONFIG['var_im'].update(evt.product_dict)
        APPCONFIG['var_im'].update(evt.mes_attr)

        if evt.mes_switch and evt.result == feature.PASS:
            pub.sendMessage(TOPIC_WORKTABLE_LOAD, status=True)

    def OnThreadDialog(self, evt):
        if evt.win_idx == self.win_idx and evt.type == 'BADCODE':
            self.thread_data_queue.put( feature.getBadCode(self, APPCONFIG) )
        elif evt.win_idx == self.win_idx and evt.type == 'SN':
            self.thread_data_queue.put(feature.getSNValue(evt.data['win']))
        elif evt.win_idx == self.win_idx and evt.type == 'MAC':
            self.thread_data_queue.put( feature.getMacValue(evt.data['win']) )
        elif evt.win_idx == self.win_idx and evt.type == 'WORKSTAGE': #工序选择弹框
            win, xml = evt.data['win'], evt.data['xml']
            self.thread_data_queue.put( feature.getWorkstage(win, xml) )
        elif evt.win_idx == self.win_idx and evt.type == "WORKSTAGE_MSGBOX": #工序需要弹出哪些输入框
            win, item_attr = evt.data['win'], evt.data['item_attr']
            self.thread_data_queue.put(feature.getWorkstageMsgBox(win, item_attr))

    def OnGetWin(self, win_idx, dev_win):
        if self.win_idx == win_idx:
            self.dev_win = dev_win

    def OnTimer(self, evt):
        try:
            self.time_text.SetLabel( arrow.now().format('YYYY-MM-DD HH:mm:ss dddd', locale='zh_cn') )
        except wx.PyAssertionError as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))

    def OnStop(self, win_idx):
        if win_idx == self.win_idx and self.product:
            self.product.stop()

    def OnDissconect(self, win_idx):
        if win_idx == self.win_idx and self.dev.alive():
            self.dev.close()

    def OnReconnct(self, win_idx):
        if win_idx == self.win_idx and not self.dev.alive():
            try:
                self.dev.connect()
            except Exception as e:
                self.message_win.section_window.section_log.AppendText(u'{}重新连接失败\n'.format(self.name))
            else:
                self.message_win.section_window.section_log.AppendText(u'{}重新连接成功\n'.format(self.name))

    #同步窗口设置
    def OnPortSet(self, setting_value, win_idx):
        if win_idx == self.win_idx:
            self.name = setting_value.get('name')
            notebook = self.GetParent()
            notebook.SetPageText(win_idx, self.name)
            self.dev_win.name_text.SetLabel(self.name)
            self.dev.apply_settings(**setting_value)

    def WorkTableLoaded(self):
        if not APPCONFIG['worktable_loaded']:
            mainframe = wx.Window.FindWindowByName('MainFrame')
            MainFrame.OnJobInfo(mainframe, None)
        return APPCONFIG['worktable_loaded']

#start test listener function
    def OnUnitTest(self, win_idx):
        if self.win_idx == win_idx:
            try:
                product_dict = { '@WN':APPCONFIG['wn'], '@AGINGTIME':APPCONFIG['agingtime']}
                product_dict['@SSID'] = '@{}_{}'.format(platform.node(), self.name)
                product_dict['@PORTID'] = str(100+ self.win_idx )
                product_dict['@VMAC'] = feature.inttomac(self.win_idx+1)

                if not self.WorkTableLoaded(): return
                self.product = Product(product_dict, self.thread_data_queue, APPCONFIG,  self)
                self.thread = threading.Thread(target=self.product.run, name=self.name)
                self.thread.start()
            except Exception as e:
                APPCONFIG['popupobj'][self.name].update({'win_idx': self.win_idx, 'first_run_by_hand': False, 'isRunning': False})
                APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
                wx.MessageBox( feature.errorencode(traceback.format_exc()), u'单元测试', style=wx.ICON_ERROR)
            finally:
                pass

    #event of clear button in bottom sizer
    def OnClear(self, evt):
        self.message_win.log_area.Clear()

    #event of input entry in top sizer
    def OnCommandEnter(self, evt):

        obj = evt.GetEventObject()
        try:
            if self.dev.alive():
                self.dev.write(bytes(obj.GetValue()+self.linefeed), write_timeout=0)
        except Exception as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
        finally:
            obj.Clear()

    def OnIdle(self, evt):
        #加延迟，读取速度太快数据显示异常
        # time.sleep(0.1)

        popupobj = APPCONFIG['popupobj']
        if isinstance(popupobj, dict):
            for key, value in popupobj.iteritems():
                if not isinstance(value, bool)  and  value.get('auto_popup', False) and value.get('first_run_by_hand', False) and not value.get('isRunning'):
                    if not popupobj.has_key('isUsing') or not popupobj['isUsing']:
                        popupobj[key]['isRunning'] = True
                        popupobj['isUsing'] = True
                        pub.sendMessage(TOPIC_START_TEST, win_idx=value['win_idx'])

        if self.dev.alive():
            data = self.dev.read_available()
            if data:
                self.message_win.AppendContent(data)

    #when a command enter append linefeed to end
    def OnLinefeed(self, evt):
        feed = evt.GetString()
        if feed == 'LF':
            self.linefeed = LINEFEED_LF
        elif feed == 'CR':
            self.linefeed = LINEFEED_CR
        elif feed == 'CR/LF':
            self.linefeed = LINEFEED_CRLF
        elif feed == 'None':
            self.linefeed = LINEFEED_NONE
        else:
            pass

#DeviceWinow to show port, stage, status info etc,
class DeviceWindow(wx.Panel):
    def __init__(self, parent,size=wx.DefaultSize, name='', win_idx=None):
        wx.Panel.__init__(self, parent=parent, name=name)
        if self.GetName():
            #assign an index number to window
            self.win_idx = win_idx
            #set window minimize size
            self.SetMinSize((-1, -1) )
            #bind popup menu event to window when left mouse press
            self.Bind(wx.EVT_CONTEXT_MENU, self.OnShowPopupMenu)
            #bind left double click event to window
            self.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)

            self.name_text = wx.StaticText(self, -1, self.GetName(), pos=(10, 10))
            self.name_text.SetForegroundColour(COLOUR_BLACK)

            self.sn_text = wx.StaticText(self, -1, 'SN', pos=(10, 30))
            self.sn_text.SetForegroundColour(COLOUR_BLACK)

            self.status_text = wx.StaticText(self, -1, '', pos=(10, 50))
            self.status_text.SetForegroundColour(COLOUR_BLACK)

            self.sn_text.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)
            self.name_text.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)
            self.status_text.Bind(wx.EVT_LEFT_DCLICK, self.OnUnitTest)
            for st in [self.sn_text, self.name_text, self.status_text]:
                st.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, encoding=wx.FONTENCODING_SYSTEM))

            pub.sendMessage(TOPIC_TRANSFER_WIN, win_idx = self.win_idx, dev_win = self)

    def OnShowPopupMenu(self, evt):
        menu = wx.Menu()
        click_position = evt.GetPosition()
        option_item = menu.Append(-1, u'单元设置' )
        stop_item = menu.Append(-1, u'停止')
        setting_item = menu.Append(-1, u'设置' )
        dissconect_item = menu.Append(-1, u'断开连接')
        reconnect_item = menu.Append(-1, u'重新连接')
        #port set
        self.Bind(wx.EVT_MENU, functools.partial(self.OnPortSet, position=click_position), setting_item)
        #stop unit test
        self.Bind(wx.EVT_MENU, self.OnStop, stop_item)
        #断开串口连接
        self.Bind(wx.EVT_MENU, self.OnDissconect, dissconect_item)
        #重新连接串口
        self.Bind(wx.EVT_MENU, self.OnReconnect, reconnect_item)
        option_item.Enable(False)
        self.PopupMenu(menu)

    def OnStop(self, evt):
        pub.sendMessage(TOPIC_STOP_TEST, win_idx=self.win_idx)

    def OnDissconect(self, evt):
        pub.sendMessage(TOPIC_DISSCONECT_SERIAL, win_idx=self.win_idx)

    def OnReconnect(self, evt):
        pub.sendMessage(TOPIC_RECONNECT_SERIAL, win_idx=self.win_idx)

    # setting serial attribute
    def OnPortSet(self, evt, position):
        data = {'setting_file': APPCONFIG['setting_file'], 'name': self.name_text.GetLabel()}
        with feature.settingdialog_factory(data, APPCONFIG['protocol']) as dlg:
            dlg.SetPosition(position)
            if dlg.ShowModal() == wx.ID_OK:
                dlg.SaveChange()
                setting_value = dlg.GetValue()
                pub.sendMessage(TOPIC_PORT_SET, setting_value=setting_value, win_idx=self.win_idx)

    def OnUnitTest(self, evt):
        try:
            if self.GetName():
                pub.sendMessage(TOPIC_START_TEST, win_idx=self.win_idx)
        except IOError as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
            wx.MessageBox(u'{} 文件不存在'.format(e.filename), u'错误', style=wx.ICON_ERROR)
        except KeyError as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
            wx.MessageBox(u'请输入工单信息', u'Warning', style=wx.ICON_WARNING)
        except Exception:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
            wx.MessageBox( feature.errorencode(traceback.format_exc()) , u'Exception', style=wx.ICON_ERROR)

#device area place device window all together
class DeviceArea(wx.Panel):
    def __init__(self, parent, rows, cols, win_list):
        """
        :param parent:
        :param rows:  窗口行数
        :param cols:  窗口列数
        :param win_list 窗口列表
        """
        wx.Panel.__init__(self, parent)
        #initialize windows, windows name list and sizer

        win_list = win_list[0:]
        win_nums = len(win_list)
        win_list +=  ['' for _ in range(cols*rows)]

        sizer = wx.GridBagSizer()
        #if window has name then place it in sizer
        idx = 0
        for row in range(rows):
            for col in range(cols):
                win_name = win_list[idx]
                if win_name:
                    APPCONFIG['popupobj'][win_name] = {}
                    dw = DeviceWindow(self, name=win_name, win_idx=idx)
                    dw.SetBackgroundColour(COLOUR_WHITE)
                    sizer.Add(dw, (row, col), (1, 1), wx.EXPAND|wx.ALL, 1)
                    idx += 1

        if win_nums <= cols:
            #when available port less than one row, set row, column auto growing
            for col in range(win_nums):
                sizer.AddGrowableCol(col)
            sizer.AddGrowableRow(0)
        else:
            #when available port more than one row, set row, column auto growing
            for col in range(cols):
                sizer.AddGrowableCol(col)
            for row in range(int(math.ceil(win_nums/(cols+0.0)))):
                sizer.AddGrowableRow(row)
            #set last cell to span the remain space
            last_row = int(math.ceil(win_nums / (cols + 0.0))) - 1
            remain_space = (last_row + 1) * cols - win_nums
            lastcell_pos = (last_row, cols - remain_space - 1)
            lastcell = sizer.FindItemAtPosition(lastcell_pos)
            lastcell.SetSpan((1, remain_space + 1))

        #attach sizer to self
        self.SetSizer(sizer)
        self.sizer = sizer

#page area place all device page all together
class PageArea(wx.Notebook):
    def __init__(self, parent, win_list ,name='PageArea'):
        wx.Notebook.__init__(self, parent)
        for idx, name in enumerate(win_list):
            page = DevicePage(self, name=name, win_idx=idx)
            self.AddPage(page, name)

        pub.subscribe(self.OnSwitchPage, TOPIC_START_TEST)

    def OnSwitchPage(self, win_idx):
        try:
            self.ChangeSelection(win_idx)
        except Exception as e:
            pass

class TestWindow(wx.Panel):
    def __init__(self, parent=None, win_list=None):
        wx.Panel.__init__(self, parent=parent)

        self.test_area = wx.SplitterWindow(self)
        self.pagearea = PageArea(self.test_area, win_list)
        self.devicearea = DeviceArea(self.test_area, 30, 3, win_list)
        self.devicearea.SetBackgroundColour(COLOUR_GRAY)
        # split window in horizontal style
        self.test_area.SplitHorizontally(window1=self.devicearea, window2=self.pagearea)
        self.test_area.SetSashPosition(150)
        self.test_area.SetMinimumPaneSize(100)

        self.tip_info = wx.InfoBar(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.test_area, 1, wx.EXPAND)
        sizer.Add(self.tip_info, 0, wx.EXPAND)
        self.SetSizer(sizer)

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, 'AutoTest', name='MainFrame')
        self._prepare()
        self.CreateWindow()
        self.CreateMenuBar()
        self.CreateTaskBar()
        self.Bind(wx.EVT_CLOSE, self.OnExitApp)
        pub.subscribe(self.OnAppconfigReceive, TOPIC_APPCONFIG_RECEIVE)

    def _prepare(self):
        if APPCONFIG['protocol'] == 'serial':
            self.win_list = feature.AvailablePort.get()
        elif APPCONFIG['protocol'] == 'telnet':
            self.win_list = ['IP{}:PORT'.format(i+1) for i in range(int(APPCONFIG['initwinnum']))]

    def  OnAppconfigReceive(self):
        bugframe = wx.Window.FindWindowByName('BugFrame', self)
        bugframe.appconfig = APPCONFIG

    def CreateWindow(self):
        self.main_window = wx.SplitterWindow(self, style=wx.SP_NOBORDER)
        self.test_window = TestWindow(self.main_window, self.win_list)
        self.mes_window = MesArea(self.main_window)
        self.main_window.SplitVertically(self.mes_window, self.test_window)
        with feature.AppSettingReader(APPCONFIG['appsetting_file'])  as s:
            if s.get('mes_area', 'value') == 'show':
                self.main_window.SplitVertically(self.mes_window, self.test_window)
            else:
                self.main_window.Unsplit(self.mes_window)

        self.main_window.SetMinimumPaneSize(5)
        self.main_window.SetSashGravity(1/3.0)

    def CreateTaskBar(self):
        # taskbaricon
        self.taskbaricon = wx.adv.TaskBarIcon()
        self.taskbaricon.SetIcon(wx.Icon(APPCONFIG['iconpath']), u'自动化测试平台')
        self.taskbaricon.ShowBalloon(u'瑞斯康达', u'自动化测试平台', 2000)
        self.taskbaricon.Bind(wx.adv.EVT_TASKBAR_MOVE, self.OnTaskBarMove)
        self.taskbaricon.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.OnTaskBarRightUp)
        self.taskbaricon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarClick)

    def OnTaskBarMove(self, evt):
        user = APPCONFIG['wn']
        app_name = u'自动化测试平台'
        ip = socket.gethostbyname(socket.gethostname())
        tip = u'用户:{}\nIP:{}'.format(user, ip)
        self.taskbaricon.SetIcon(wx.Icon(APPCONFIG['iconpath']), tip)

    def OnTaskBarRightUp(self, evt):
        menu = wx.Menu()
        quit_item = menu.Append(-1 , u'退出')
        open_item = menu.Append(-1, u'打开')
        menu.Bind(wx.EVT_MENU, self.OnOpenApp, open_item)
        menu.Bind(wx.EVT_MENU, self.OnExitApp, quit_item)
        self.taskbaricon.PopupMenu(menu)

    def OnOpenApp(self, evt):
        self.Restore()

    def OnExitApp(self, evt):
        wx.Exit()

    def OnTaskBarClick(self, evt):
        self.Restore()

    def OnOpenMenu(self, evt):
        obj = evt.GetEventObject()
        if obj.GetTitle() == u'帮助(&H)':
            testing_item = obj.FindItemByPosition(1)
            repaire_item = obj.FindItemByPosition(2)
            testing_item.Enable(APPCONFIG['testing_account_right'])
            repaire_item.Enable(APPCONFIG['repaire_account_right'])

    #create menu bar function
    def CreateMenuBar(self):
        menubar = wx.MenuBar()
        self.Bind(wx.EVT_MENU_OPEN, self.OnOpenMenu, menubar)
        #help menu
        help_menu = wx.Menu()
        about_item = help_menu.Append(-1, u'关于' )
        testing_item = help_menu.AppendCheckItem(-1, u'调试', u'仅限于测试账号')
        repaire_item = help_menu.AppendCheckItem(-1, u'维修')

        self.Bind(wx.EVT_MENU, self.OnShowAbout, about_item)
        self.Bind(wx.EVT_MENU, self.OnTestingAccount, testing_item)
        self.Bind(wx.EVT_MENU, self.OnRepair, repaire_item)
        #view menu
        view_menu = wx.Menu()
        show_mes_area = view_menu.AppendCheckItem(-1, u'显示MES区')
        with feature.AppSettingReader(APPCONFIG['appsetting_file']) as setting:
            if setting.get('mes_area', 'value') == 'show':
                show_mes_area.Check(True)
            else:
                show_mes_area.Check(False)
        self.Bind(wx.EVT_MENU, self.OnShowMesArea, show_mes_area)
        #setting menu
        setting_menu = wx.Menu()
        jobinfo_item = setting_menu.Append(-1, u'工单信息输入')
        downlaod_item = setting_menu.Append(-1, u'软件下载')
        autopoup_item = setting_menu.AppendCheckItem(-1, u'SN自动弹框')
        workstage_item = setting_menu.AppendCheckItem(-1, u'工序自动弹框')
        setting_item = setting_menu.Append(-1, u'参数设置')

        if APPCONFIG['popup_sn_flag']:
            autopoup_item.Check(True)
            for name in self.win_list:
                APPCONFIG['popupobj'][name].update({'auto_popup': True})

        self.Bind(wx.EVT_MENU, functools.partial(MainFrame.OnJobInfo, self), jobinfo_item)
        self.Bind(wx.EVT_MENU, self.OnSoftDownload, downlaod_item)
        self.Bind(wx.EVT_MENU, self.OnAutoPopup, autopoup_item)
        self.Bind(wx.EVT_MENU, self.OnAutoWorkstage, workstage_item)
        self.Bind(wx.EVT_MENU, self.OnSetting, setting_item)

        sync_menu = wx.Menu()
        update_config_file_item = sync_menu.Append(-1, u"更新配置文件")
        self.Bind(wx.EVT_MENU, self.OnUpdateConfigFile, update_config_file_item)

        #tool menu
        tool_menu = wx.Menu()
        bug_item = tool_menu.Append(-1, u'工具合集')
        self.Bind(wx.EVT_MENU, self.OnBug, bug_item)
        menubar.Append(view_menu, u'视图(&V)')
        menubar.Append(setting_menu, u'设置(&S)')
        menubar.Append(sync_menu, u'更新(&U)')
        menubar.Append(tool_menu, u'工具(&T)')
        menubar.Append(help_menu, u'帮助(&H)')
        self.SetMenuBar(menubar)

    def OnShowMesArea(self, evt):
        main_frame = wx.Window.FindWindowByName('MainFrame')
        main_win = main_frame.main_window
        test_win = main_frame.test_window
        mes_win = main_frame.mes_window

        with feature.AppSettingReader(APPCONFIG['appsetting_file'])  as s:
            if evt.IsChecked():
                main_win.SplitVertically(mes_win, test_win)
                s.set('mes_area', {'value':'show'})
            else:
                main_win.Unsplit(mes_win)
                s.set('mes_area', {'value': 'hide'})

    def OnUpdateConfigFile(self, evt):
        msg, ret_status = feature.update_config_file(APPCONFIG['ftp_base_config_dir_admin'], APPCONFIG['config_file'])
        if not ret_status:
            wx.MessageBox(msg,  u'配置文件异常', style=wx.OK  | wx.CENTER | wx.ICON_WARNING)

    def OnSetting(self, evt):
        setting_frame = feature.SettingFrame(self, title='设置', appconfig=APPCONFIG)
        setting_frame.SetInitialSize((800, 600))
        setting_frame.CentreOnParent()
        setting_frame.Show()
        setting_frame.Refresh()

    def OnAutoPopup(self, evt):
        APPCONFIG['popup_sn_flag'] = evt.IsChecked()
        notebook = self.test_window.pagearea
        for idx in range(notebook.GetPageCount()):
            if not APPCONFIG['popupobj'].has_key(notebook.GetPageText(idx)):
                APPCONFIG['popupobj'][notebook.GetPageText(idx)] = {}
            APPCONFIG['popupobj'][notebook.GetPageText(idx)].update( {'auto_popup':evt.IsChecked() } )

    def OnAutoWorkstage(self, evt):
        APPCONFIG['workstage_flag'] = evt.IsChecked()

    def OnBug(self, evt):
        bugframe = feature.BugFrame(self,  title=u'工具',size=(960, 450) ,appconfig=APPCONFIG)
        bugframe.CentreOnParent()
        bugframe.Show()


    def OnSoftDownload(self, evt):
        win = feature.DownLoadWindow(self, u'软件下载', size=(1000, -1), appconfig=APPCONFIG)
        win.SetIcon(wx.Icon(APPCONFIG['iconpath']))
        win.CenterOnParent()
        win.ShowWithEffect(wx.SHOW_EFFECT_EXPAND, 0)
        win.ShowWithoutActivating()

    @staticmethod
    def OnJobInfo(self, evt):
        send_status = True
        workjobinfo_dialog = WorkJobInfoDialog(self)
        if not workjobinfo_dialog.AssignWorkJobInfo() : return
        worksql_value, linesql_value, stasql_value, tipmsg = feature.query_linestation_info(APPCONFIG)
        assign_status, assign_msg = feature.assignMesAttr(APPCONFIG)
        if not (worksql_value and linesql_value and stasql_value and assign_status ):
            tipmsg +=  assign_msg
            send_status = False
            wx.MessageBox(tipmsg, u'警告', style=wx.ICON_WARNING|wx.OK|wx.CENTER)

        if send_status:feature.record_mes_query(APPCONFIG)
        pub.sendMessage(TOPIC_WORKTABLE_LOAD, status=send_status)
        workjobinfo_dialog.Destroy()

    def OnTestingAccount(self, evt):
        repaire_account_checked = evt.GetEventObject().FindItemByPosition(2).IsChecked()
        APPCONFIG['worktable_had_changed'] = True
        APPCONFIG['worktable_loaded'] = False
        APPCONFIG['mes_cursor'].close()
        APPCONFIG['mes_conn'].close()
        APPCONFIG['log_cursor'].close()
        APPCONFIG['log_conn'].close()

        if repaire_account_checked and evt.IsChecked():
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='已连接到测试数据库(维修账号)')
        elif evt.IsChecked() and repaire_account_checked is False:
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='已连接到测试数据库')
        elif evt.IsChecked() is False and repaire_account_checked :
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='维修账号')
        else:
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='')

        if evt.IsChecked():
            mes_username = base64.b64decode(APPCONFIG['mes_db_username_testdb'])
            mes_password = base64.b64decode(APPCONFIG['mes_db_password_testdb'])
            mes_uri = base64.b64decode(APPCONFIG['mes_db_uri_testdb'])
            APPCONFIG['debug_mode'] = True
            APPCONFIG['mes_conn'] = cx_Oracle.connect(mes_username, mes_password, mes_uri)
            APPCONFIG['mes_cursor'] = APPCONFIG['mes_conn'].cursor()

            APPCONFIG['log_conn'] = MySQLdb.connect(APPCONFIG['log_db_serverip_testdb'], APPCONFIG['log_db_username_testdb'],
                                    APPCONFIG['log_db_password_testdb'], APPCONFIG['log_db_dbname_testdb'], charset='utf8')
            APPCONFIG['log_cursor'] = APPCONFIG['log_conn'].cursor()
        else:
            mes_username = base64.b64decode(APPCONFIG['mes_db_username'])
            mes_password = base64.b64decode(APPCONFIG['mes_db_password'])
            mes_uri = base64.b64decode(APPCONFIG['mes_db_uri'])
            APPCONFIG['debug_mode'] = False
            APPCONFIG['mes_conn'] = cx_Oracle.connect(mes_username, mes_password, mes_uri)
            APPCONFIG['mes_cursor'] = APPCONFIG['mes_conn'].cursor()
            APPCONFIG['log_conn'] = MySQLdb.connect(APPCONFIG['log_db_serverip'], APPCONFIG['log_db_username'],
                                    APPCONFIG['log_db_password'], APPCONFIG['log_db_dbname'], charset='utf8')
            APPCONFIG['log_cursor'] = APPCONFIG['log_conn'].cursor()

    def OnRepair(self, evt):
        testing_account_checked = evt.GetEventObject().FindItemByPosition(1).IsChecked()

        if testing_account_checked and evt.IsChecked():
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='已连接到测试数据库(维修账号)')
        elif evt.IsChecked() and testing_account_checked is False:
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='维修账号')
        elif evt.IsChecked() is False and testing_account_checked:
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='已连接到测试数据库')
        else:
            pub.sendMessage(TOPIC_MESDB_CHANGE, msg='')

        APPCONFIG['repaire_mode'] = evt.IsChecked()
        APPCONFIG['worktable_had_changed'] = True

    #show about info
    def OnShowAbout(self, evt):
        info = wx.adv.AboutDialogInfo()
        info.SetName(__appname__)
        info.SetVersion(__version__)
        info.SetCopyright(u'Copyright © 2017-2018 瑞斯康达科技发展股份有限公司 保留一切权利')
        # info.Description = 'For raisecom company autotest'
        info.SetWebSite('http://www.raisecom.com.cn/', u'瑞斯康达科技发展股份有限公司')
        info.AddArtist('Kitty')
        info.AddDeveloper('Tappy')
        wx.adv.AboutBox(info)
        self.mes_window.Hide()
        self.main_window.Layout()
        self.Layout()


class WorkJobInfoDialog(wx.Dialog):
    def __init__(self, parent):
        extern_StationCode = APPCONFIG['mes_attr']['extern_StationCode']
        extern_SubLineCode = APPCONFIG['mes_attr']['extern_SubLineCode']
        extern_WJTableName = APPCONFIG['mes_attr']['extern_WJTableName']
        op_workers = APPCONFIG['mes_attr']['op_workers']

        wx.Dialog.__init__(self, parent, title=u'工单信息')
        size_ST = (60, -1)

        #工序输入
        self.stationST = wx.StaticText(self, -1, u'工序:', size=size_ST)
        self.stationTC = wx.TextCtrl(self, -1, extern_StationCode)

        #线体选择
        self.lineST = wx.StaticText(self, -1, u'线体:', size=size_ST)
        choice_sql = 'select DISTINCT linecode, line from DMSNEW.WORKPRODUCE'
        sql_value = APPCONFIG['mes_cursor'].execute(choice_sql).fetchall()
        line_choice = []
        if sql_value:
            for line_code, _ in sql_value:
                line_choice.append(line_code)

        self.line_choice = wx.Choice(self, choices=line_choice)
        self.line_choice.SetStringSelection(extern_SubLineCode)

        #工单输入
        self.wjtST = wx.StaticText(self, -1, u'工单号:', size=size_ST)
        self.wjtTC = wx.TextCtrl(self, -1, extern_WJTableName)

        #投入人数
        self.workers_ST = wx.StaticText(self, -1, u'投入人数:', size=size_ST)
        self.workers_SP = wx.SpinCtrl(self, -1, initial=op_workers )

        sizer_station = wx.BoxSizer(wx.HORIZONTAL)
        sizer_station.Add(self.stationST, 0, wx.GROW | wx.CENTER)
        sizer_station.Add(self.stationTC, 1, wx.GROW | wx.CENTER)

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

    def AssignWorkJobInfo(self):
        if self.ShowModal() == wx.ID_OK:
            APPCONFIG['mes_attr']['extern_StationCode'] = self.stationTC.GetValue().strip()
            APPCONFIG['mes_attr']['extern_SubLineCode'] = self.line_choice.GetStringSelection()
            APPCONFIG['mes_attr']['extern_WJTableName'] = self.wjtTC.GetValue().strip()
            APPCONFIG['mes_attr']['op_workers'] = self.workers_SP.GetValue()
            self.Destroy()
            return True
        self.Destroy()
        return False

class ReadyListCtrl(feature.ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        feature.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.BORDER_NONE)
        self.itemDataMap = {}
        column_fields = [(u'NO', 35), (u'SN', 210)]
        for idx, header in enumerate(column_fields):
            self.InsertColumn(idx, header[0], width=header[-1])
            # self.RefreshData()
        listmix.ColumnSorterMixin.__init__(self, self.GetColumnCount())

    def PopulateData(self):
        for idx, data  in enumerate(feature.get_available_sn(APPCONFIG)):
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
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))

    def GetListCtrl(self):
        return self

class FinishListCtrl(feature.ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        feature.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT | wx.BORDER_NONE)
        self.itemDataMap = {}
        column_fields = [(u'NO', 35 ), (u'工序号', 50 ), (u'条码', 210 ), (u'工序', 40),
                         (u'线体', 40), (u'不良现象', 60), (u'电性/外观', 70 ), (u'扫描时间', 100)]
        for idx, header in enumerate(column_fields):
            self.InsertColumn(idx, header[0], width=header[-1])
            # self.RefreshData()
        listmix.ColumnSorterMixin.__init__(self, self.GetColumnCount())

    def PopulateData(self):
        extern_SubAttemperCode = APPCONFIG['mes_attr']['extern_SubAttemperCode']
        extern_AttempterCode = APPCONFIG['mes_attr']['extern_AttempterCode']
        sql = "select rownum no,subid,barcode,testposition,line_code2,qulity_plobolem,REPAIR,scan_time from dmsnew.{} where subattemper_code='{}' " \
              "order by scan_time desc, barcode".format( extern_AttempterCode, extern_SubAttemperCode)
        sql_value = APPCONFIG['mes_cursor'].execute(sql).fetchall()
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
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))

    def GetListCtrl(self):
        return self

class MesArea(wx.SplitterWindow):
    def __init__(self, parent=None):
        wx.SplitterWindow.__init__(self, parent=parent, name='MesArea')
        self.CreateTopArea()
        self.CreateBottomArea()
        self.SplitHorizontally(self.top, self.bottom, 0)
        self.SetSashGravity(1/4)
        self.SetMinimumPaneSize(5)

    def CreateTopArea(self):
        self.top = wx.Panel(self)
        self.review = wx.TextCtrl(self.top, style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.soft_download = wx.Button(self.top, -1, label=u'下载软件')
        self.sop_download = wx.Button(self.top, -1, label=u'下载指导书')
        self.Bind(wx.EVT_BUTTON, self.OnSoftDownload, self.soft_download)
        self.Bind(wx.EVT_BUTTON, self.OnSopDownload, self.sop_download)

        sizer_download = wx.BoxSizer(wx.HORIZONTAL)
        sizer_download.Add(self.soft_download, 1, wx.GROW | wx.CENTER)
        sizer_download.Add(self.sop_download, 1, wx.GROW | wx.CENTER)

        sizer_review = wx.StaticBoxSizer(wx.VERTICAL, self.top, u'特殊评审说明')
        sizer_review.Add(self.review, 1, wx.GROW | wx.CENTER)
        sizer_review.Add(sizer_download, 0, wx.GROW | wx.CENTER)
        self.top.SetSizer(sizer_review)
        pub.subscribe(self.OnRefresh, TOPIC_WORKTABLE_LOAD)

    def OnRefresh(self, status):
        if status:
            self.ShowReview()
            self.ready_list.RefreshData()
            self.finish_list.RefreshData()

    def ShowReview(self):
        #segment33 特殊评审说明
        self.review.SetValue(APPCONFIG['mes_attr']['workjob_review'])

    def OnSoftDownload(self, evt):
        try:
            win = feature.DownLoadWindow(self, u'软件下载', size=(1000, -1), appconfig=APPCONFIG)
            win.SetIcon(wx.Icon(APPCONFIG['iconpath']))
            win.CenterOnParent()
            win.ShowWithEffect(wx.SHOW_EFFECT_EXPAND, 0)
            win.ShowWithoutActivating()
        except KeyError as e:
            self.infobar.ShowMessage(u'请先输入工单信息')

    def OnSopDownload(self, evt):
        try:
            win = feature.DownLoadSopWindow(self, u'SOP下载', size=(1000, -1), appconfig=APPCONFIG)
            win.SetIcon(wx.Icon(APPCONFIG['iconpath']))
            win.CenterOnParent()
            win.ShowWithEffect(wx.SHOW_EFFECT_EXPAND, 0)
            win.ShowWithoutActivating()
        except KeyError as e:
            self.infobar.ShowMessage(u'请先输入工单信息')

    def CreateBottomArea(self):
        self.bottom = wx.Panel(self)
        self.bottom_splitter = wx.SplitterWindow(self.bottom)

        self.bottom_ready_panel = wx.Panel(self.bottom_splitter)
        self.ready_list = ReadyListCtrl(self.bottom_ready_panel)
        ready_bz = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_ready_panel, u'待测条码区')
        ready_bz.Add(self.ready_list, 1, wx.EXPAND)
        self.bottom_ready_panel.SetSizer(ready_bz)

        self.bottom_finish_panel = wx.Panel(self.bottom_splitter)
        self.finish_list =  FinishListCtrl(self.bottom_finish_panel)
        finish_bz = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_finish_panel, u'已测条码区')
        finish_bz.Add(self.finish_list, 1, wx.EXPAND)
        self.bottom_finish_panel.SetSizer(finish_bz)

        self.bottom_splitter.SplitVertically(self.bottom_ready_panel, self.bottom_finish_panel)
        self.bottom_splitter.SetSashGravity(1/3.0)
        self.infobar = wx.InfoBar(self.bottom)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.bottom_splitter, 1, wx.EXPAND)
        sizer_main.Add(self.infobar, 0, wx.EXPAND)
        self.bottom.SetSizer(sizer_main)

#Login Window
class LoginDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title=u'登陆:' )
        self.job_number_ST = wx.StaticText(self, -1, u'MES账号:')
        self.job_number_TC = wx.TextCtrl(self, -1, '')

        job_sizer = wx.BoxSizer(wx.HORIZONTAL)
        job_sizer.Add(self.job_number_ST, 0, wx.GROW|wx.CENTER)
        job_sizer.Add(self.job_number_TC, 1, wx.GROW|wx.CENTER)

        self.password_ST = wx.StaticText(self, -1, u'MES密码:')
        self.password_TC = wx.TextCtrl(self, -1, '', style=wx.TE_PASSWORD)

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
        wx.GetApp()

    def SetWN(self):
        ret_status = False
        while True:
            if self.ShowModal() == wx.ID_OK:
                job_number = self.job_number_TC.GetValue().strip()
                password = self.password_TC.GetValue()

                sql = "select dispname, passwords, userid from dmsnew.rs_user1 where userid='{}'".format(job_number)
                sql_value = APPCONFIG['mes_cursor'].execute(sql).fetchone()

                if sql_value is None:
                    self.SetTitle('登陆:无效账号')
                else:
                    mes_uname, mes_password, mes_uid = sql_value[0], sql_value[1], sql_value[2]
                    if mes_password == password:
                        APPCONFIG['wn'] = mes_uid
                        APPCONFIG['wn_name'] = mes_uname
                        ret_status = True

                        sql = "select rolesn from dmsnew.rs_role where rolesn in (select rolesn from " \
                              " DMSNEW.RS_USERROLE where usersn in (select usersn from DMSNEW.RS_USER1 where userid='{}')  )".format(mes_uid)
                        sql_value = APPCONFIG['mes_cursor'].execute(sql).fetchall()

                        if not sql_value :
                            APPCONFIG['testing_account_right'] = False
                            APPCONFIG['repaire_account_right'] = False
                        else:
                            for rolesn in sql_value:
                                if rolesn[0] in [1, 3]:
                                    APPCONFIG['testing_account_right'] = True
                                    APPCONFIG['repaire_account_right'] = True
                                    break
                                elif rolesn[0] in [24]:
                                    APPCONFIG['testing_account_right'] = False
                                    APPCONFIG['repaire_account_right'] = True
                                    break
                        break
                    else:
                        self.SetTitle('登陆:密码错误')
            else:
                ret_status = False
                break
        self.Destroy()
        return ret_status

class App(wx.App, wit.InspectionMixin):
    def __init__(self):
        wx.App.__init__(self)

    def OnInit(self):
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
        try:
            framesize = (1000, 600)
            self.Init()
            self.frame = MainFrame()
            self.frame.CenterOnScreen()
            self.frame.SetInitialSize(framesize)
            self.frame.SetMinSize((0, 0))
            self.frame.SetIcon(wx.Icon(APPCONFIG['iconpath']))
            self.frame.Show(True)
            if not self.check(): return False
            if not self.login(): return False
            return True
        except Exception as e:
            APPCONFIG['logger'].error(feature.errorencode(traceback.format_exc()))
            wx.MessageBox( feature.errorencode(traceback.format_exc()), u'软件启动异常', style=wx.ICON_ERROR)
            return False
        return True

    def check(self):
        if APPCONFIG['protocol'] == 'serial':
            if feature.AvailablePort.get() == []:
                dlg = wx.MessageDialog(None, u'串口被占用或没有可用的串口', u'警告', style=wx.OK | wx.CANCEL | wx.CENTER | wx.ICON_WARNING)
                dlg.SetOKCancelLabels('OK', u'删除本地配置文件')
                if dlg.ShowModal() == wx.ID_CANCEL:
                    os.remove(APPCONFIG['setting_file'])
                dlg.Destroy()
                return False

        return True

    def login(self):
        login_dlg = LoginDialog(self.frame)
        if login_dlg.SetWN() == False:
            self.OnExit()
            return False

        return True

    def OnExit(self):
        self.frame.taskbaricon.RemoveIcon()
        APPCONFIG['mes_cursor'].close()
        APPCONFIG['mes_conn'].close()
        APPCONFIG['log_cursor'].close()
        APPCONFIG['log_conn'].close()
        return 0

def main(appconfig):
    global APPCONFIG
    APPCONFIG = appconfig
    app = App()
    app.MainLoop()


