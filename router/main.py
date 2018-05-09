#coding:utf-8
import sys
import wx
import os
import wx.html
import time
import wx.adv
import textwrap
import threading
import signal
from wx.py.shell import ShellFrame
from io import open
from lxml import etree
import wx.html2 as webview
from device.device import *
reload(sys)
sys.setdefaultencoding('utf-8')
__version__ = '1.0'

DATA_DIR = os.path.join(os.getcwd(), 'data')
SETTING_DIR = os.path.join(os.getcwd(), 'setting')
CONFIG_FILE = os.path.join( SETTING_DIR, 'device.xml' )
PLUS_IMAGE = os.path.join(DATA_DIR, 'plus_green.png')
INFO_IMAGE = os.path.join(DATA_DIR, 'info.png')
ICON__IMAGE = os.path.join(DATA_DIR, 'logo.ico')
THREAD_LOCK = threading.RLock()

class WebPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.wv = webview.WebView.New(self)
        self.Bind(webview.EVT_WEBVIEW_LOADED, self.OnWebViewLoaded, self.wv)
        self.current = 'http://www.baidu.com'
        btnsizer = wx.BoxSizer()

        btn = wx.Button(self, label='<--', style=wx.BU_EXACTFIT)
        btnsizer.Add(btn, 0, wx.EXPAND|wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnBack, btn)
        self.Bind(wx.EVT_UPDATE_UI, self.OnCheckCanGoBack, btn)

        btn = wx.Button(self, label='-->', style=wx.BU_EXACTFIT)
        btnsizer.Add(btn, 0, wx.EXPAND | wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnPrev, btn)
        self.Bind(wx.EVT_UPDATE_UI, self.OnCheckCanGoForward, btn)

        btn = wx.Button(self, label='Refresh', style=wx.BU_EXACTFIT)
        btnsizer.Add(btn, 0, wx.EXPAND | wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, btn)

        btn = wx.Button(self, label='Home', style=wx.BU_EXACTFIT)
        btnsizer.Add(btn, 0, wx.EXPAND | wx.ALL, 2)
        self.Bind(wx.EVT_BUTTON, self.OnHome, btn)

        self.location = wx.ComboBox(self, style=wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)
        self.location.Append(self.current)
        self.Bind(wx.EVT_COMBOBOX, self.OnLocationSelect, self.location)
        self.location.Bind(wx.EVT_TEXT_ENTER, self.OnLocationEnter)
        btnsizer.Add(self.location, 1, wx.EXPAND|wx.ALL, 2)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(btnsizer, 0, wx.EXPAND)
        sizer.Add(self.wv, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def OnLocationEnter(self, evt):
        url = self.location.GetValue()
        self.location.Append(url)
        self.wv.LoadURL(url)

    def OnLocationSelect(self, evt):
        url = self.location.GetStringSelection()
        self.wv.LoadURL(url)

    def OnWebViewLoaded(self, evt):
        self.current = evt.GetURL()
        self.location.SetValue(self.current)

    def OnPrev(self, evt):
        self.wv.GoForward()

    def OnBack(self, evt):
        self.wv.GoBack()

    def OnRefresh(self, evt):
        self.wv.Reload()

    def OnHome(self, evt):
        self.wv.LoadURL('http://192.168.1.1')

    def OnCheckCanGoBack(self, evt):
        evt.Enable(self.wv.CanGoBack())

    def OnCheckCanGoForward(self, evt):
        evt.Enable( self.wv.CanGoForward())

class AboutDialog(wx.Dialog):
    def __init__(self, parent, datafile='', size=wx.DefaultSize, title='About'):
        wx.Dialog.__init__(self, parent=parent, size=size, title=title)

        html = wx.html.HtmlWindow(self)
        html.LoadFile(datafile)
        button = wx.Button(self, wx.ID_OK, 'OK')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(html, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.SetSizer(sizer)
        self.Layout()

class AddDialog(wx.Dialog):
    def __init__(self, parent, size=wx.DefaultSize, title='添加'):
        wx.Dialog.__init__(self, parent=parent, size=size, title=title, style=wx.DEFAULT_FRAME_STYLE)

        self.pool = {}
        self.lable = [('type','设备类型:'), ('url','URL:'), ('username','用户名:'), ('password','密码:'), ('class', 'class')]
        mainsizer = wx.BoxSizer(orient=wx.VERTICAL)
        for idx, label in enumerate(self.lable):
            text = wx.StaticText(self, label=label[1], style=wx.ALIGN_LEFT, size=(80, -1))
            ctrl = wx.TextCtrl(self)
            self.pool[str(idx)] = ctrl
            sizer = wx.BoxSizer()
            sizer.Add(text, 0, wx.EXPAND)
            sizer.Add(ctrl, 1, wx.EXPAND)
            mainsizer.Add(sizer, 0, wx.EXPAND)

        okbtn = wx.Button(self, wx.ID_OK, 'Ok')
        cancelbtn = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okbtn)
        btns.AddButton(cancelbtn )
        btns.Realize()
        mainsizer.AddStretchSpacer(1)
        mainsizer.Add(btns, 0, wx.EXPAND)
        self.SetSizer(mainsizer)

    def ShowModal(self):
        if super(AddDialog, self).ShowModal() == wx.ID_CANCEL: return
        parser = etree.XMLParser(remove_blank_text=True)
        device_xml = etree.parse(CONFIG_FILE, parser=parser)
        root = device_xml.getroot()
        element = etree.Element('li')
        for idx, ctl in self.pool.iteritems():
            element.set(self.lable[int(idx)][0], ctl.GetValue().strip())

        for node in root:
            if node.attrib == element.attrib:
                return

        root.append(element)
        with open(CONFIG_FILE, 'wb+') as f:
            f.write(etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True) )

class MainFrame(wx.Frame):
    def __init__(self, title):
        wx.Frame.__init__(self, parent=None, title=title)
        panel = wx.Panel(self)
        self.bin_file = None
        self.isUpgrading = False
        self.SetIcon(wx.Icon(ICON__IMAGE) )
        self.thread = None
        text_size = (95, 18)

        device_type_sier = wx.BoxSizer()
        device_type_text = wx.StaticText(panel, label=u'①选择设备类型:', style=wx.ALIGN_LEFT, size=text_size)

        parser = etree.XMLParser(remove_blank_text=True)
        device_xml = etree.parse(CONFIG_FILE, parser=parser)
        device_choice = [ device.get('type') for device in device_xml.iter('li')]

        device_type_ctl = wx.ComboBox(panel, value=device_choice[0], choices=device_choice, style=wx.CB_READONLY)
        self.device_type_ctl = device_type_ctl
        device_type_sier.Add(device_type_text, 0, wx.EXPAND|wx.RIGHT, 10)
        device_type_sier.Add(device_type_ctl, 1, wx.EXPAND, 10)

        file_sizer = wx.BoxSizer()
        file_text = wx.StaticText(panel, label=u'②选择升级文件:', style=wx.ALIGN_LEFT, size=text_size)

        file_ctl = wx.FilePickerCtrl(panel, message=u'升级文件' ,style=wx.FLP_CHANGE_DIR|wx.FLP_USE_TEXTCTRL)
        file_sizer.Add(file_text, 0, wx.EXPAND|wx.RIGHT, 10)
        file_sizer.Add(file_ctl, 1, wx.EXPAND, 10)


        version_sizer = wx.BoxSizer()
        version_text = wx.StaticText(panel, label=u'③填写软件版本:', style=wx.ALIGN_LEFT, size=text_size)
        self.version_ctl = version_ctl = wx.TextCtrl(panel)
        version_sizer.Add(version_text, 0, wx.EXPAND | wx.RIGHT, 10)
        version_sizer.Add(version_ctl, 1, wx.EXPAND, 10)

        upgrade_button = wx.Button(panel, label=u'升级')
        self.device_panel = wx.Panel(panel)

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer.Add(device_type_sier, 0, wx.EXPAND)
        sizer.Add(file_sizer, 0, wx.EXPAND)
        sizer.Add(version_sizer, 0, wx.EXPAND)
        sizer.Add(self.device_panel, 1, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        sizer.Add(upgrade_button, 0, wx.EXPAND)
        panel.SetSizer(sizer)
        self.CreateMenuBar()
        #self.CreateToolBar()
        self.CreateStatusBar(style=wx.STB_SIZEGRIP)
        self.Bind(wx.EVT_FILEPICKER_CHANGED, self.OnFileSelected, file_ctl)
        self.Bind(wx.EVT_BUTTON, self.OnUpgrade, upgrade_button)

    def upgrade(self, node, data):
        device_class = globals()[node.get('class')]
        node_dict = node.attrib
        device_ins = device_class(node_dict['url'], node_dict['username'], node_dict['password'], data=data)
        device_ins.modify_sn_and_reboot()

    def OnUpgrade(self, evt):
            self.StatusBar.SetStatusText('Ready')
            xml = etree.parse(CONFIG_FILE)
            node = xml.xpath('.//li[@type="{}"]'.format(self.device_type_ctl.GetStringSelection() ))[0]
            if self.thread and not self.thread.isAlive():
                self.thread = None

            if self.thread is None:
                sn_dlg = wx.TextEntryDialog(self, u'请输入SN', 'SN')
                if sn_dlg.ShowModal() == wx.ID_OK:
                    sn = sn_dlg.GetValue().strip().upper()
                    sn_dlg.Destroy()
                else:
                    sn_dlg.Destroy()
                    return

                mac_dlg = wx.TextEntryDialog(self, u'请输入SN', 'SN')
                if mac_dlg.ShowModal() == wx.ID_OK:
                    mac = mac_dlg.GetValue().strip().lower()
                    mac_dlg.Destroy()
                else:
                    mac_dlg.Destroy()
                    return

                data = {'sn': sn, 'mac': mac}
                self.thread = threading.Thread(target=self.upgrade, args=(node, data))
                self.thread.start()


    def OnFileSelected(self, evt):
        self.bin_file = evt.GetPath()

    def ShowTime(self, evt):
        time_str =  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.StatusBar.SetStatusText(time_str)

    def CreateStatusBar(self, **kwargs):
        super(MainFrame, self).CreateStatusBar(**kwargs)
        self.StatusBar.SetStatusText('Ready')

    def CreateToolBar(self, **kwarg):
        super(MainFrame, self).CreateToolBar(**kwarg)
        toolbar = self.ToolBar
        addtool = toolbar.AddTool(-1, label='添加', shortHelp='添加', bitmap=wx.Bitmap(PLUS_IMAGE))
        abouttool = toolbar.AddTool(-1, label='关于', shortHelp='关于', bitmap=wx.Bitmap(INFO_IMAGE))
        self.Bind(wx.EVT_TOOL, self.DeviceAdd, addtool)
        self.Bind(wx.EVT_TOOL, self.AboutMsg, abouttool)
        toolbar.Realize()

    def CreateMenuBar(self):
        menubar = wx.MenuBar()

        setting_menu = wx.Menu()
        add__mi = setting_menu.Append(-1, u'添加')
        self.Bind(wx.EVT_MENU, self.DeviceAdd, add__mi)

        about_menu = wx.Menu()
        about_mi = about_menu.Append(-1, '关于')
        shell_item = about_menu.Append(-1, u'Shell工具')
        self.Bind(wx.EVT_MENU, self.AboutMsg, about_mi)
        self.Bind(wx.EVT_MENU, self.OnShell, shell_item)

        menubar.Append(setting_menu, '设置')
        menubar.Append(about_menu, '关于')

        self.SetMenuBar(menubar)

    def OnShell(self, evt):
        frame = ShellFrame(self)
        frame.CentreOnParent()
        frame.Show()

    def DeviceAdd(self, evt):
        dlg = AddDialog(self)
        dlg.ShowModal()

    def AboutMsg(self, evt):
        description = open( os.path.join(DATA_DIR, 'raisecom.txt'), 'r' , encoding='utf-8').read()
        description = textwrap.fill(description, width=40)
        aboutInfo = wx.adv.AboutDialogInfo()
        aboutInfo.SetName("瑞斯康达")
        aboutInfo.SetVersion(__version__)
        aboutInfo.SetDescription((description))
        aboutInfo.SetCopyright("Copyright (C) 2017 瑞斯康达科技发展股份有限公司 保留一切权利 京ICP备13011671号")
        aboutInfo.SetWebSite("http://raisecom.com.cn/")
        aboutInfo.AddDeveloper("ChenJie")
        wx.adv.AboutBox(aboutInfo)

class RouterApp(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def OnInit(self):
        self.frame = MainFrame(title='固件升级')
        self.SetTopWindow(self.frame)
        self.frame.CenterOnScreen()
        self.frame.SetInitialSize( (500, 300))
        self.frame.SetMinSize((0, 0))
        self.frame.ShowWithEffect(wx.SHOW_EFFECT_ROLL_TO_RIGHT, 1)
        self.frame.Show()
        self.frame.Refresh()
        return True

    def OnExit(self):
        return 0

App = RouterApp()
App.MainLoop()
os.kill(os.getpid(), signal.SIGTERM)

