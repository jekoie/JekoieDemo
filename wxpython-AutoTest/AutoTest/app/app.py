# coding=utf-8
from __future__ import division
import os
import wx
import sys
import math
import socket
import traceback
import functools
from lxml import etree
import wx.lib.mixins.inspection as wit
from wx.lib.pubsub import pub
from datetime import datetime
from ui import ui, tool
from config.config import Config

reload(sys)
sys.setdefaultencoding('utf-8')
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'

#device area place device window all together
class DeviceArea(wx.Panel):
    windows = []
    def __init__(self, parent, rows, cols, win_list):
        """
        :param parent:
        :param rows:  窗口行数
        :param cols:  窗口列数
        :param win_list 窗口列表
        """
        wx.Panel.__init__(self, parent)
        #initialize windows, windows name list and sizer

        win_list = win_list[:]
        win_nums = len(win_list)
        win_list +=  ['' for _ in range(cols*rows)]

        sizer = wx.GridBagSizer()
        #if window has name then place it in sizer
        idx = 0
        for row in range(rows):
            for col in range(cols):
                win_name = win_list[idx]
                if win_name:
                    # dw = ui.SingleDeviceWindow(self, name=win_name, win_idx=idx)
                    dw = ui.devicewindow_factory(Config.mode['mode'], self, win_name, idx)
                    dw.SetBackgroundColour(Config.colour_white)
                    self.__class__.windows.append(dw)
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

    def __iter__(self):
        return iter(self.__class__.windows)

    def __len__(self):
        return len(self.__class__.windows)

#page area place all device page all together
class PageArea(wx.Notebook):
    windows = []
    def __init__(self, parent, win_list, name='PageArea'):
        wx.Notebook.__init__(self, parent)
        if Config.mode['mode'] == 'double': win_list = 2*win_list
        for idx, name in enumerate(win_list):
            page = ui.DevicePage(self, name=name, win_idx=idx)
            self.__class__.windows.append(page)
            self.AddPage(page, name)

    def __iter__(self):
        return iter(self.__class__.windows)

    def __len__(self):
        return len(self.__class__.windows)

class TestWindow(wx.Panel):
    def __init__(self, parent=None, win_list=None):
        wx.Panel.__init__(self, parent=parent)

        self.test_area = wx.SplitterWindow(self)
        self.pagearea = PageArea(self.test_area, win_list)
        self.devicearea = DeviceArea(self.test_area, 30, 3, win_list)
        self.devicearea.SetBackgroundColour(Config.colour_gray)
        # split window in horizontal style
        self.test_area.SplitHorizontally(window1=self.devicearea, window2=self.pagearea)
        self.test_area.SetSashPosition(150)
        self.test_area.SetMinimumPaneSize(100)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.test_area, 1, wx.EXPAND)
        self.SetSizer(sizer)

        try:
            self.GetWindowsForConfig()
            self.InitDevices()
        except Exception:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

    def InitDevices(self):
        root = etree.parse(Config.devfile, Config.parser_without_comments).getroot()
        for idx in range(len(self.pagearea)):
            node = root.find("./li[@win='{}']".format(idx))
            if node is not None:
                if Config.mode['mode'] == 'single' and node.get('protocol', '') == Config.protocol:
                    tool.create_device(node.attrib, idx)
                    devwin = self.devicearea.windows[idx]
                    pagewin = self.pagearea.windows[idx]

                    devwin.dev1_name.SetLabel(node.get('name'))
                    pagewin.SetName(node.get('name'))

                    notebook = pagewin.GetParent()
                    notebook.SetPageText(idx, node.get('name'))

                if Config.mode['mode'] == 'double':
                    tool.create_device(node.attrib, idx)
                    devwin = self.devicearea.windows[divmod(idx, 2)[0]]
                    pagewin = self.pagearea.windows[idx]
                    pagewin.SetName(node.get('name'))

                    if idx%2:
                        devwin.dev2_name.SetLabel(node.get('name'))
                    else:
                        devwin.dev1_name.SetLabel(node.get('name'))

                    notebook = pagewin.GetParent()
                    notebook.SetPageText(idx, node.get('name'))

    def GetWindowsForConfig(self):
        devwins, pagewins = list(self.devicearea), list(self.pagearea)
        if Config.mode['mode'] == 'single':
            for idx in range(len(devwins)):
                Config.windows.update( {devwins[idx]: (pagewins[idx], None)})
        else:
            for idx in range(len(devwins)):
                Config.windows.update({devwins[idx]: (pagewins[2*idx], pagewins[2*idx + 1])})

        for idx in range(len(Config.windows)):
            Config.popup.update({idx: {'auto_popup': False, 'used':False, 'byhand':False}})

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, 'AutoTest', name='MainFrame')
        self.InitWinList()
        self.CreateWindow()
        self.CreateMenuBar()
        self.CreateTaskBar()
        self.Bind(wx.EVT_CLOSE, self.OnExitApp)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnIdle(self, evt):
        for key, value in Config.popup.items():
            if value['auto_popup'] and  value['byhand'] and not value['used']:
                Config.windows.keys()[key].OnUnitTest(None)

    def InitWinList(self):
        if Config.protocol == 'serial':
            self.win_list = ['COM'  for i in range(int(Config.initwinnum)) ]
        elif Config.protocol == 'telnet':
            self.win_list = ['IP{}:PORT'.format(i+1) for i in range(int(Config.initwinnum))]

    def CreateWindow(self):
        self.main_window = wx.SplitterWindow(self, style=wx.SP_NOBORDER)
        self.test_window = TestWindow(self.main_window, self.win_list)
        self.mes_window = MesArea(self.main_window)
        self.main_window.SplitVertically(self.mes_window, self.test_window)

        if Config.showmesarea:
            self.main_window.SplitVertically(self.mes_window, self.test_window)
        else:
            self.main_window.Unsplit(self.mes_window)

        self.main_window.SetMinimumPaneSize(5)
        self.main_window.SetSashGravity(1/3.0)

    def CreateTaskBar(self):
        # taskbaricon
        self.taskbaricon = wx.adv.TaskBarIcon()
        self.taskbaricon.SetIcon(wx.Icon(Config.logofile), u'自动化测试平台')
        self.taskbaricon.ShowBalloon(u'瑞斯康达', u'自动化测试平台', 2000)
        self.taskbaricon.Bind(wx.adv.EVT_TASKBAR_MOVE, self.OnTaskBarMove)
        self.taskbaricon.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.OnTaskBarRightUp)
        self.taskbaricon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarClick)

    def OnTaskBarMove(self, evt):
        user = '{}({})'.format(Config.wn, Config.wnname)
        ip = socket.gethostbyname(socket.gethostname())
        tip = u'用户:{}\nIP:{}'.format(user, ip)
        self.taskbaricon.SetIcon(wx.Icon(Config.logofile), tip)

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
        try:
            for dev in  Config.windows:
                dev.thread.stop()
        except Exception:
            Config.logger.error(tool.errorencode(traceback.format_exc()))

        wx.Exit()

    def OnTaskBarClick(self, evt):
        self.Restore()

    def OnMenuBar(self, evt):
        obj = evt.GetEventObject()
        if obj and  obj.GetTitle() == u'帮助(&H)':
            testing_item = obj.FindItemByPosition(1)
            repaire_item = obj.FindItemByPosition(2)
            workorder_item = obj.FindItemByPosition(3)
            testing_item.Enable(Config.right['test_right'])
            repaire_item.Enable(Config.right['repaire_right'])
            workorder_item.Enable(Config.right['workorder_right'])

    #create menu bar function
    def CreateMenuBar(self):
        menubar = wx.MenuBar()
        self.Bind(wx.EVT_MENU_OPEN, self.OnMenuBar, menubar)
        #help menu
        help_menu = wx.Menu()
        about_item = help_menu.Append(-1, u'关于' )
        testing_item = help_menu.AppendCheckItem(-1, u'调试')
        repaire_item = help_menu.AppendCheckItem(-1, u'维修')
        workorder_item = help_menu.AppendCheckItem(-1, u'工单号')

        workorder_item.Check(Config.mode['workorder_mode'])
        self.Bind(wx.EVT_MENU, self.OnShowAbout, about_item)
        self.Bind(wx.EVT_MENU, self.OnTestingAccount, testing_item)
        self.Bind(wx.EVT_MENU, self.OnRepair, repaire_item)
        self.Bind(wx.EVT_MENU, self.OnNeedWorkOrder, workorder_item)
        #view menu
        view_menu = wx.Menu()
        show_mes_area = view_menu.AppendCheckItem(-1, u'显示MES区')
        if Config.showmesarea:
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

        autopoup_item.Check(Config.autosn)
        workstage_item.Check(Config.autoworkstage)

        for idx in range(len(Config.windows)):
            Config.popup[idx].update({'auto_popup': Config.autosn})

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

    @staticmethod
    def OnJobInfo(self, evt):
        workjobinfo_dialog = ui.WorkJobInfoDialog(self)
        if not workjobinfo_dialog.GetWorkJobInfo(): return
        flag_workjob, flag_linecode, flag_stationcode, tipmsg = tool.validate_workjob()
        flag_attr, attr_msg  = tool.get_mes_attr()
        if flag_workjob&flag_linecode&flag_stationcode&flag_attr:
            Config.worktable_loaded = True
            Config.worktable_changed = True
            tool.record_mes_query()
            pub.sendMessage(Config.topic_notify_mesarea, status=True)
        else:
            tipmsg +=  attr_msg
            Config.worktable_loaded = False
            Config.worktable_changed = False
            wx.MessageBox(tipmsg, '警告', style=wx.ICON_WARNING|wx.OK|wx.CENTER)

    def OnShowMesArea(self, evt):
        main_frame = wx.Window.FindWindowByName('MainFrame')
        main_win = main_frame.main_window
        test_win = main_frame.test_window
        mes_win = main_frame.mes_window

        if evt.IsChecked():
            main_win.SplitVertically(mes_win, test_win)
            Config.showmesarea = True
        else:
            main_win.Unsplit(mes_win)
            Config.showmesarea = False

    def OnUpdateConfigFile(self, evt):
        msg, ret_status = tool.update_config_file(Config.ftpbase, Config.configfile)
        if not ret_status:
            wx.MessageBox(msg,  u'配置文件异常', style=wx.OK  | wx.CENTER | wx.ICON_WARNING)

    def OnSetting(self, evt):
        setting_frame = ui.SettingFrame(self, title='设置')
        setting_frame.SetSize((400, 350))
        setting_frame.CentreOnParent()
        setting_frame.Show()

    def OnAutoPopup(self, evt):
        Config.autosn = evt.IsChecked()
        for idx in range(len(Config.windows)):
            Config.popup[idx].update({'auto_popup': evt.IsChecked()})

    def OnAutoWorkstage(self, evt):
        Config.autoworkstage = evt.IsChecked()

    def OnBug(self, evt):
        bugframe = ui.BugFrame(self,  title=u'工具',size=(960, 450) )
        bugframe.CentreOnParent()
        bugframe.Show()

    def OnSoftDownload(self, evt):
        try:
            win = ui.DownLoadWindow(self, u'软件下载', size=(1000, -1))
            win.CenterOnParent()
            win.ShowWithEffect(wx.SHOW_EFFECT_EXPAND, 0)
            win.ShowWithoutActivating()
        except KeyError:
            wx.MessageBox('请先输入工单信息', '警告', style=wx.ICON_WARNING|wx.CENTER, parent=self)

    def OnTestingAccount(self, evt):
        Config.switch_db(evt.IsChecked())
        pub.sendMessage(Config.topic_db_change)

    def OnRepair(self, evt):
        Config.mode['repaire_mode'] = evt.IsChecked()
        pub.sendMessage(Config.topic_db_change)

    def OnNeedWorkOrder(self, evt):
        Config.mode['workorder_mode'] = evt.IsChecked()

    #show about info
    def OnShowAbout(self, evt):
        info = wx.adv.AboutDialogInfo()
        info.SetName(Config.__appname__)
        info.SetVersion(Config.__version__)
        info.SetCopyright(u'Copyright © 2017-{} 深圳工艺部'.format(datetime.now().year))
        # info.Description = 'For raisecom company autotest'
        info.SetWebSite('http://www.raisecom.com.cn/', u'瑞斯康达科技发展股份有限公司')
        info.AddDeveloper('工艺部-陈杰')
        wx.adv.AboutBox(info, self)

class MesArea(wx.SplitterWindow):
    def __init__(self, parent=None):
        wx.SplitterWindow.__init__(self, parent=parent, name='MesArea')
        self.CreateTopArea()
        self.CreateBottomArea()
        self.SplitHorizontally(self.top, self.bottom, 0)
        self.SetSashGravity(1/4)
        self.SetMinimumPaneSize(5)
        pub.subscribe(self.OnRefresh, Config.topic_notify_mesarea)

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

    def OnRefresh(self, status):
        if status:
            self.ShowReview()
            self.ready_list.RefreshData()
            self.finish_list.RefreshData()

    def ShowReview(self):
        self.review.SetValue(Config.mes_attr['workjob_review'])

    def OnSoftDownload(self, evt):
        try:
            win = ui.DownLoadWindow(self, u'软件下载', size=(1000, -1))
            win.CenterOnParent()
            win.ShowWithEffect(wx.SHOW_EFFECT_EXPAND, 0)
            win.ShowWithoutActivating()
        except KeyError as e:
            self.infobar.ShowMessage(u'请先输入工单信息')

    def OnSopDownload(self, evt):
        try:
            win = ui.DownLoadSopWindow(self, u'SOP下载', size=(1000, -1))
            win.CenterOnParent()
            win.ShowWithEffect(wx.SHOW_EFFECT_EXPAND, 0)
            win.ShowWithoutActivating()
        except KeyError as e:
            self.infobar.ShowMessage(u'请先输入工单信息')

    def CreateBottomArea(self):
        self.bottom = wx.Panel(self)
        self.bottom_splitter = wx.SplitterWindow(self.bottom)

        self.bottom_ready_panel = wx.Panel(self.bottom_splitter)
        self.ready_list = ui.ReadyListCtrl(self.bottom_ready_panel)
        ready_bz = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_ready_panel, u'待测条码区')
        ready_bz.Add(self.ready_list, 1, wx.EXPAND)
        self.bottom_ready_panel.SetSizer(ready_bz)

        self.bottom_finish_panel = wx.Panel(self.bottom_splitter)
        self.finish_list = ui.FinishListCtrl(self.bottom_finish_panel)
        finish_bz = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_finish_panel, u'已测条码区')
        finish_bz.Add(self.finish_list, 1, wx.EXPAND)
        self.bottom_finish_panel.SetSizer(finish_bz)

        self.bottom_splitter.SplitVertically(self.bottom_ready_panel, self.bottom_finish_panel)
        self.bottom_splitter.SetSashGravity(1 / 3.0)
        self.infobar = wx.InfoBar(self.bottom)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.bottom_splitter, 1, wx.EXPAND)
        sizer_main.Add(self.infobar, 0, wx.EXPAND)
        self.bottom.SetSizer(sizer_main)

class App(wx.App, wit.InspectionMixin):
    def __init__(self):
        wx.App.__init__(self)

    def OnInit(self):
        self.Init()
        self.prepare()
        if self.upgrade_software(): return False
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
        self.frame = MainFrame()
        self.frame.CenterOnScreen()
        self.frame.SetInitialSize((1000, 600))
        self.frame.SetMinSize((0, 0))
        self.frame.SetIcon(wx.Icon(Config.logofile))
        self.frame.Show(True)
        if not self.login(): return False
        self.finish()
        return True

    def login(self):
        login_dlg = ui.LoginDialog(self.frame)
        if login_dlg.SetWN() == False:
            return False
        return True

    def OnExit(self):
        with tool.AppSettingReader() as s:
            s.set('showmesarea', {'value': str(Config.showmesarea)})
            s.set('autosn', {'value': str(Config.autosn)})
            s.set('autoworkstage', {'value': str(Config.autoworkstage)})
            s.set('stationcode', {'value':  Config.mes_attr['extern_StationCode']})
            s.set('linecode', {'value': Config.mes_attr['extern_SubLineCode']})
            s.set('operators', {'value': str(Config.mes_attr['op_workers']) })
            s.set('worktable', {'value':   Config.mes_attr['extern_WJTableName'] })
            s.set('initwinnum', {'value': str(Config.initwinnum) })
            s.set('mode', {'value': Config.mode['mode']})
            s.set('protocol', {'value': Config.protocol})

            s.set('wn', {'value': Config.wn})

            s.set('autopos', {'value': str(Config.autopos)})
            s.set('posx', {'value': str(Config.posx)})
            s.set('posy', {'value': str(Config.posy)})

        Config.close()
        return 0

    def finish(self):
        if not tool.time_sync():
            wx.MessageBox(u'同步服务器(192.168.60.70)时间失败', 'Warning', style=wx.OK | wx.ICON_EXCLAMATION)
        pub.sendMessage(Config.topic_db_change)

    def upgrade_software(self):
        need_update = False
        try:
            soft_value = Config.db.fetchone("select softname, author, version, path from soft_table where softname=\"{}\"".format(Config.__appname__))
            if soft_value is not None:
                softname, author, version, path = soft_value
                if version > Config.__version__:
                    wx.MessageBox(u'发现新版本{}{}, {}'.format(softname, version, path) ,u'升级软件', style=wx.OK|wx.ICON_WARNING)
                    need_update = True
        except Exception as e:
            need_update = False
        finally:
            return need_update

    def prepare(self):
        Config.connect_normal_db()
        Config.genfilepath( os.getcwd() )
        with tool.AppSettingReader() as s:
            Config.showmesarea = eval( s.get('showmesarea', 'value') )
            Config.autosn = eval( s.get('autosn', 'value') )
            Config.autoworkstage = eval(s.get('autoworkstage', 'value'))
            Config.mes_attr['extern_StationCode'] = s.get('stationcode', 'value')
            Config.mes_attr['extern_SubLineCode'] = s.get('linecode', 'value')
            Config.mes_attr['extern_WJTableName'] =  s.get('worktable', 'value')
            Config.mes_attr['op_workers'] = int( s.get('operators', 'value') )

            Config.initwinnum = int( s.get('initwinnum', 'value') )
            Config.mode['mode'] = s.get('mode', 'value')
            Config.protocol = s.get('protocol', 'value')

            Config.wn = s.get('wn', 'value')

            Config.autopos = eval( s.get('autopos', 'value') )
            Config.posx = int(s.get('posx', 'value'))
            Config.posy = int(s.get('posy', 'value'))

            Config.autopos =  True if int(Config.initwinnum) > 1 else False

def main():
    app = App()
    app.MainLoop()


