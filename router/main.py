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
from builtins import open
from lxml import etree
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

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer.Add(device_type_sier, 0, wx.EXPAND)
        sizer.Add(file_sizer, 0, wx.EXPAND)
        sizer.Add(version_sizer, 0, wx.EXPAND)
        sizer.Add(upgrade_button, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        self.CreateMenuBar()
        #self.CreateToolBar()
        self.CreateStatusBar(style=wx.STB_SIZEGRIP)
        self.Bind(wx.EVT_FILEPICKER_CHANGED, self.OnFileSelected, file_ctl)
        self.Bind(wx.EVT_BUTTON, self.OnUpgrade, upgrade_button)

    def upgrade(self, node, win):
        THREAD_LOCK.acquire()
        win.StatusBar.SetStatusText('正在升级中')
        device_class = globals()[node.get('class')]
        node_dict = node.attrib
        msg = ''
        try:
            device_ins = device_class(node_dict['url'], node_dict['username'], node_dict['password'], win.bin_file)
            device_ins.relogin()
            device_ins.modify_data(node_dict.get('data', ''))
            if device_ins.upgrade() == False:
                raise TypeError('upgrade failed')
            device_ins.wait_device_to_reset()

            device_ins.relogin()
            device_ins.factory_reset()
            device_ins.wait_device_to_reset()

            device_ins.relogin()
            if device_ins.check_version(self.version_ctl.GetValue()):
                msg += '版本校验成功 '
            else:
                msg += '版本校验失败 '
            msg += '固件升级成功 '
            win.StatusBar.SetStatusText(msg)
        except Exception as e:
            #wx.MessageBox(traceback.format_exc(), 'error')
            msg += '升级失败'
            win.StatusBar.SetStatusText(msg)
        finally:
            if self.version_ctl.GetValue().strip() !=  '':
                device_ins.close()
            THREAD_LOCK.release()

    def OnUpgrade(self, evt):
        if self.bin_file is not None:
            self.StatusBar.SetStatusText('Ready')
            xml = etree.parse(CONFIG_FILE)
            node = xml.xpath('.//li[@type="{}"]'.format(self.device_type_ctl.GetStringSelection() ))[0]

            if THREAD_LOCK._RLock__count == 0:
                threading.Thread(target=self.upgrade, args=(node, self)).start()
            else:
                self.StatusBar.SetStatusText('请等待当前升级完毕')

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

