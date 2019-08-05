from ui import ui, mixin
from config.config import Config
from PyQt5.QtWidgets import (QMainWindow, QSplitter, QApplication, QFrame, QHBoxLayout,
                             QTabWidget, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import socket
import platform

#测试单元区域
@mixin.DebugClass
class TestUnitArea(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)

        layout = QHBoxLayout()
        for win_idx in range(Config.INITWIN_NUM):
            testunit = ui.TestUnitFrame(win_idx)
            layout.addWidget(testunit)
            Config.RC[win_idx].update({'win': testunit} )

        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

#测试结果区域
@mixin.DebugClass
class TestResultArea(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        if Config.INITWIN_NUM == 2 and Config.SCREEN_MODE: #分屏模式
            layout.setSpacing(1)
            win0 = ui.TestResultFrame(0)
            win1 = ui.TestResultFrame(1)
            layout.addWidget(win0)
            layout.addWidget(win1)
            Config.RC[0].update({'page': win0})
            Config.RC[1].update({'page': win1})
        elif Config.INITWIN_NUM == 2 and not Config.SCREEN_MODE: #分页模式
            tab = QTabWidget()
            layout.addWidget(tab)
            for win_idx in range(Config.INITWIN_NUM):
                item = Config.DEV_XML_TREE.find('//li[@win="{}"]'.format(win_idx))
                tabwin = ui.TestResultFrame(win_idx)
                tab.addTab(tabwin, item.get('name', 'COM') )
                Config.RC[win_idx].update({'page': tabwin})
            Config.RC['tab'] = tab
        else:
            win0 = ui.TestResultFrame(0)
            Config.RC[0].update({'page': win0})
            layout.addWidget(win0)

#主程序窗口
@mixin.DebugClass
class MainWindow(QMainWindow):
    EXIT_CODE_REBOOT = 520
    def __init__(self):
        super().__init__()
        Config.initialize()
        self.initUI()

    def initUI(self):
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.spliter = QSplitter(Qt.Vertical)
        self.spliter.addWidget(TestUnitArea())
        self.spliter.addWidget(TestResultArea())
        self.spliter.setHandleWidth(1)
        self.setCentralWidget(self.spliter)

        tool_menu = QMenu('工具', self.menuBar())
        tool_menu.addAction('数据监视', self.onDebugWindow)
        tool_menu.addAction('记录查询', self.onViewData)
        tool_menu.addAction('异常信息', self.onExceptionWindow)

        setting_menu = QMenu('选项', self.menuBar())
        setting_menu.addAction('参数设置', self.onSetting)
        setting_menu.addAction('重启', self.onRestart)

        help_menu = QMenu('帮助', self.menuBar())
        help_menu.addAction('关于', self.onAbout)

        self.menuBar().addMenu(setting_menu)
        self.menuBar().addMenu(tool_menu)
        self.menuBar().addMenu(help_menu)

        QApplication.setWindowIcon(QIcon(Config.LOGO_IMG))
        QApplication.instance().aboutToQuit.connect(self.onApplicationQuit)
        QApplication.setOrganizationName(Config.ORGANIZATION)
        QApplication.setApplicationName(Config.APP_NAME)
        QApplication.setApplicationVersion(Config.APP_VERSION)
        self.restoreQSettings()
        self.createSystemTray()

    def onDebugWindow(self):
        if not ui.DebugDialog.prev_actived:
            self.debugWin = ui.DebugDialog()
            self.debugWin.show()
        else:
            QApplication.setActiveWindow(ui.DebugDialog.prev_window)
            ui.DebugDialog.prev_window.showNormal()

    def onViewData(self):
        if not ui.SearchWindow.prev_actived:
            self.searchWin = ui.SearchWindow()
            self.searchWin.show()
        else:
            QApplication.setActiveWindow(ui.SearchWindow.prev_window)
            ui.SearchWindow.prev_window.showNormal()

    def onExceptionWindow(self):
        if not ui.ExceptionWindow.prev_actived:
            self.excptionWin = ui.ExceptionWindow()
            self.excptionWin.show()
        else:
            QApplication.setActiveWindow(ui.ExceptionWindow.prev_window)
            ui.ExceptionWindow.prev_window.showNormal()

    def restoreQSettings(self):
        main_win_geo = Config.QSETTING.value('MainWindow/geometry')
        main_win_centerwgt_state = Config.QSETTING.value('MainWindow/CenterWidget/state')

        if main_win_geo: self.restoreGeometry(main_win_geo)
        if main_win_centerwgt_state: self.spliter.restoreState(main_win_centerwgt_state)

    def onSetting(self):
        dlg = ui.SettingDialog(self)
        dlg.move(self.x() + 50, self.y() + 50 )
        dlg.exec()

    def onRestart(self):
        QApplication.exit(self.EXIT_CODE_REBOOT)

    def onAbout(self):
        pass

    def createSystemTray(self):
        self.systray = QSystemTrayIcon(self)
        self.systray.setIcon(QIcon(Config.LOGO_IMG))
        self.systray.show()

        trayMenu = QMenu()
        trayMenu.addAction('最大化', self.showMaximized)
        trayMenu.addAction('最小化', self.showMinimized)
        trayMenu.addAction('显示窗口', self.showNormal)
        stayOnTop = QAction('总在最前', trayMenu, checkable=True, triggered=self.stayOnTop)
        trayMenu.addAction(stayOnTop)
        trayMenu.addSeparator()
        trayMenu.addAction('退出', QApplication.quit)

        username = platform.node()
        ip = socket.gethostbyname(socket.gethostname())

        self.systray.setToolTip('用户：{}\nIP:{}'.format(username, ip))
        self.systray.activated.connect(self.onSystemTrayActivated)
        self.systray.setContextMenu(trayMenu)

    def onSystemTrayActivated(self, reason):
        if reason in [QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger]:
            self.showNormal()

    def stayOnTop(self):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.sender().isChecked() )
        self.show()

    def onApplicationQuit(self):
        Config.QSETTING.setValue('MainWindow/geometry', self.saveGeometry())
        Config.QSETTING.setValue('MainWindow/CenterWidget/state', self.spliter.saveState())
        Config.finalize()
        self.systray.deleteLater()

    def closeEvent(self, event):
        Config.QSETTING.setValue('MainWindow/geometry', self.saveGeometry())
        Config.QSETTING.setValue('MainWindow/CenterWidget/state', self.spliter.saveState() )

        if self.systray.isVisible():
            self.hide()
            event.ignore()
