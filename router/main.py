#coding:utf-8
import wx
import wx.adv
import sys
import os
import traceback
import textwrap
import threading
import signal
import wx.lib.mixins.inspection as wit
from wx.py.shell import ShellFrame
from io import open
from lxml import etree
from device import device

reload(sys)
sys.setdefaultencoding('utf-8')

__version__ =  '2.0'

class Config(object):
    #目录
    datadir = os.path.join(os.getcwd(), 'data')
    settingdir = os.path.join(os.getcwd(), 'setting')
    bindir = os.path.join(os.getcwd(), 'bin')
    #文件
    configfile = os.path.join(settingdir, 'device.xml' )
    logofile = os.path.join(datadir, 'logo.ico')
    descfile = os.path.join(datadir, 'raisecom.txt')
    chromedriver = os.path.join(bindir, 'chromedriver.exe')

    #弹框标记
    popup_mac = False
    popup_sn = False
    show_step = False

    #产品信息
    mac = None
    sn = None
    firmware = None
    version = None

    #结果
    pass_ = 'PASS'
    fail = 'FAIL'

    #配置文件对象
    configobj = None

    #wx 颜色
    color_aqua = wx.Colour(32, 178, 170)
    color_red = wx.Colour(249, 0, 0)
    color_green = wx.Colour(0, 249, 0)


os.environ['PATH'] = Config.bindir

class StatusPanel(wx.Panel):
    def __init__(self, parent, name=''):
        wx.Panel.__init__(self, parent=parent, name=name, style=wx.BORDER_STATIC)

        self.sn_label = wx.StaticText(self, -1, 'SN:')
        self.sn_text = wx.StaticText(self, -1, '未设置')
        sizer_sn = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sn.Add(self.sn_label, 0, wx.LEFT, 5)
        sizer_sn.Add(self.sn_text, 0, wx.LEFT, 5)

        self.mac_label = wx.StaticText(self , -1, 'MAC:')
        self.mac_text = wx.StaticText(self , -1, '未设置')
        sizer_mac = wx.BoxSizer(wx.HORIZONTAL)
        sizer_mac.Add(self.mac_label, 0, wx.LEFT, 5)
        sizer_mac.Add(self.mac_text, 0, wx.LEFT, 5)

        self.status_label = wx.StaticText(self , -1, '状态:')
        self.status_text = wx.StaticText(self , -1, 'Ready')
        sizer_status = wx.BoxSizer(wx.HORIZONTAL)
        sizer_status.Add(self.status_label, 0, wx.LEFT, 5)
        sizer_status.Add(self.status_text, 0, wx.LEFT, 5)

        self.result_label = wx.StaticText(self , -1, '结果:')
        self.result_text = wx.StaticText(self, -1, 'Ready')
        sizer_result = wx.BoxSizer(wx.HORIZONTAL)
        sizer_result.Add(self.result_label,  0, wx.LEFT, 5)
        sizer_result.Add(self.result_text,  0, wx.LEFT, 5)

        #异常信息
        self.traceback_text = wx.StaticText(self, -1, '')
        self.traceback_text.SetForegroundColour(wx.BLUE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany([sizer_sn, sizer_mac, sizer_status, sizer_result, (self.traceback_text, 1, wx.EXPAND|wx.LEFT, 5)])
        self.SetSizer(sizer)

        self.sizer = sizer

    def setbackgroundcolour(self, color):
        self.SetBackgroundColour(color)
        self.Refresh()

    def setsn(self, sn):
        wx.CallAfter(self.sn_text.SetLabel, sn)
        wx.CallAfter(self.Refresh)

    def setmac(self, mac):
        wx.CallAfter(self.mac_text.SetLabel, mac)
        wx.CallAfter(self.Refresh)

    def setstatus(self, status):
        append_status = self.status_text.GetLabel()
        append_status += status + '\n'
        status_msg = append_status if Config.show_step else status
        wx.CallAfter(self.status_text.SetLabel, status_msg)
        wx.CallAfter(self.Refresh)
        self.sizer.Layout()

    def setresult(self, result):
        wx.CallAfter(self.result_text.SetLabel, result)
        wx.CallAfter(self.Refresh)

    def settraceback(self, traceback):
        wx.CallAfter(self.traceback_text.SetLabel, traceback)
        wx.CallAfter(self.Refresh)


class MainFrame(wx.Frame):
    def __init__(self, title):
        wx.Frame.__init__(self, parent=None, title=title)
        self.panel = wx.Panel(self)
        self.SetIcon(wx.Icon(Config.logofile) )

        text_size = (95, 18)
        #设备控件
        device_type_sier = wx.BoxSizer()
        device_type_text = wx.StaticText(self.panel, label=u'①选择设备类型:', style=wx.ALIGN_LEFT, size=text_size)

        parser = etree.XMLParser(remove_blank_text=True, encoding='utf-8', remove_comments=True)
        Config.configobj  = etree.parse(Config.configfile, parser=parser)
        device_choice = [ device.get('type') for device in Config.configobj.iter('li')]

        self.device_type_ctl = wx.ComboBox(self.panel, value=device_choice[0], choices=device_choice, style=wx.CB_READONLY)
        device_type_sier.Add(device_type_text, 0, wx.EXPAND|wx.RIGHT, 10)
        device_type_sier.Add(self.device_type_ctl, 1, wx.EXPAND, 10)

        #文件控件
        file_sizer = wx.BoxSizer()
        file_text = wx.StaticText(self.panel, label=u'②选择升级文件:', style=wx.ALIGN_LEFT, size=text_size)

        self.file_ctl = file_ctl = wx.FilePickerCtrl(self.panel, message=u'升级文件' ,style=wx.FLP_CHANGE_DIR|wx.FLP_USE_TEXTCTRL)
        file_sizer.Add(file_text, 0, wx.EXPAND|wx.RIGHT, 10)
        file_sizer.Add(file_ctl, 1, wx.EXPAND, 10)

        #版本控件
        version_sizer = wx.BoxSizer()
        version_text = wx.StaticText(self.panel, label=u'③填写软件版本:', style=wx.ALIGN_LEFT, size=text_size)
        self.version_ctl = version_ctl = wx.TextCtrl(self.panel)
        version_sizer.Add(version_text, 0, wx.EXPAND | wx.RIGHT, 10)
        version_sizer.Add(version_ctl, 1, wx.EXPAND, 10)

        #升级
        upgrade_button = wx.Button(self.panel, label=u'升级')
        self.Bind(wx.EVT_BUTTON, self.OnUpgrade, upgrade_button)

        #状态
        self.status_panel = StatusPanel(self.panel)

        #主sizer
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer.Add(device_type_sier, 0, wx.EXPAND)
        sizer.Add(file_sizer, 0, wx.EXPAND)
        sizer.Add(version_sizer, 0, wx.EXPAND)
        sizer.Add(self.status_panel, 1, wx.EXPAND)
        sizer.Add(upgrade_button, 0, wx.EXPAND)

        self.panel.SetSizer(sizer)
        self.CreateMenuBar()

        #右键菜单
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnShowPopupMenu, self.status_panel)

        #线程
        self.thread = None

    def OnShowPopupMenu(self, evt):
        menu = wx.Menu()
        stop_item = menu.Append(-1, u'停止')
        self.Bind(wx.EVT_MENU, self.OnStop, stop_item)
        self.PopupMenu(menu)

    def OnStop(self, evt):
        if self.thread and self.thread.is_alive():
            self.thread.stop()

    def prepare(self):
        self.status_panel.settraceback('')
        self.status_panel.status_text.SetLabel('')
        self.status_panel.setresult('Ready')
        Config.version = self.version_ctl.GetValue()
        Config.firmware = self.file_ctl.GetPath()

        if Config.popup_sn:
            Config.sn = wx.GetTextFromUser('请输入SN', 'SN').upper()
            self.status_panel.setsn(Config.sn)

        if Config.popup_mac:
            Config.mac = wx.GetTextFromUser('请输入MAC', 'MAC').upper()
            self.status_panel.setmac(Config.mac)

    def OnUpgrade(self, evt):
        try:
            if self.thread is None or not self.thread.is_alive():
                node = Config.configobj.xpath('.//li[@type="{}"]'.format(self.device_type_ctl.GetStringSelection()))[0]
                node_attrs = dict(node.attrib)
                node_attrs.update({'config':Config, 'statuspanel': self.status_panel})

                class_ = getattr(device, node_attrs.get('class'))
                self.prepare()
                instance = class_(**node_attrs)
                self.thread = threading.Thread(target=instance.run, name=class_)
                setattr(self.thread, 'stop', instance.stop)
                self.thread.start()
        except Exception as e:
            wx.MessageBox(traceback.format_exc(), '异常', style=wx.ICON_WARNING|wx.OK)


    def CreateMenuBar(self):
        menubar = wx.MenuBar()

        setting_menu = wx.Menu()
        sn_item = setting_menu.AppendCheckItem(-1, '弹出SN框')
        mac_item = setting_menu.AppendCheckItem(-1, '弹出MAC框')
        step_item = setting_menu.AppendCheckItem(-1, '显示运行步骤')

        self.Bind(wx.EVT_MENU, self.OnSN, sn_item)
        self.Bind(wx.EVT_MENU, self.OnMAC, mac_item)
        self.Bind(wx.EVT_MENU, self.OnStep, step_item)

        about_menu = wx.Menu()
        about_item = about_menu.Append(-1, '关于')
        shell_item = about_menu.Append(-1, 'Shell工具')
        self.Bind(wx.EVT_MENU, self.AboutMsg, about_item)
        self.Bind(wx.EVT_MENU, self.OnShell, shell_item)
        menubar.Append(setting_menu, '设置')
        menubar.Append(about_menu, '关于')
        self.SetMenuBar(menubar)

    def OnSN(self, evt):
        Config.popup_sn = evt.IsChecked()

    def OnMAC(self, evt):
        Config.popup_mac = evt.IsChecked()

    def OnStep(self, evt):
        Config.show_step = evt.IsChecked()

    def OnShell(self, evt):
        frame = ShellFrame(self)
        frame.CentreOnParent()
        frame.Show()

    def AboutMsg(self, evt):
        description = open(Config.descfile , 'r' , encoding='utf-8').read()
        description = textwrap.fill(description, width=40)
        aboutInfo = wx.adv.AboutDialogInfo()
        aboutInfo.SetName("瑞斯康达")
        aboutInfo.SetVersion(Config.version)
        aboutInfo.SetDescription((description))
        aboutInfo.SetCopyright("Copyright (C) 2018 瑞斯康达科技发展股份有限公司 保留一切权利 京ICP备13011671号")
        aboutInfo.SetWebSite("http://raisecom.com.cn/")
        aboutInfo.AddDeveloper("工艺部-陈杰")
        wx.adv.AboutBox(aboutInfo)

class RouterApp(wx.App, wit.InspectionMixin):
    def __init__(self):
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        self.frame = MainFrame(title='固件升级')
        self.frame.SetInitialSize((500, 300))
        self.frame.SetMinSize((0, 0))
        self.SetTopWindow(self.frame)
        self.frame.CenterOnScreen()
        self.frame.Show()
        return True

    def OnExit(self):
        return 0

App = RouterApp()
App.MainLoop()
os.kill(os.getpid(), signal.SIGTERM)
