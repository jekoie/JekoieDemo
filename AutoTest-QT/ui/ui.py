import os
import pandas as pd
from communicate.communicate import DevStatus
from config.config import Config
from PyQt5.QtCore import Qt, QThread, QSysInfo, QSize, QAbstractTableModel, QVariant, QStringListModel, QThreadPool
from PyQt5.QtWidgets import (QDialog, QFormLayout, QComboBox, QGroupBox, QHBoxLayout, QRadioButton,QVBoxLayout, QFileDialog,
                             QDialogButtonBox, QFrame, QLabel, QPushButton, QMenu, QTableWidget, QHeaderView, QTabWidget, QStyle,
                             QAbstractItemView, QTableWidgetItem, QMessageBox, QTextEdit, QListWidget, QStackedWidget, QLineEdit
                             ,QTableView, QApplication, QWidget, QCompleter)
from PyQt5.QtGui import QPalette, QColor, QTextDocument, QIcon
from serial.tools import list_ports
from script.script import Script
from script import mix
from bitstring import BitArray
from ui import mixin
from pubsub import pub
from db import db
from . import step
import io
import traceback

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

@mixin.DebugClass
class FindTextEdit(QWidget):
    def __init__(self):
        super().__init__()
        self.isHide = False

        self.searchLineEdit = QLineEdit(placeholderText='search', returnPressed=self.handle_search)
        self.searchLineEdit.setStyleSheet('.QLineEdit {border-radius: 5px;}')
        self.searchCompleter = QCompleter()
        self.searchCompleter.setFilterMode(Qt.MatchContains)
        self.searchList = QStringListModel()
        self.searchCompleter.setModel(self.searchList)
        self.searchCompleter.setMaxVisibleItems(10)
        self.searchLineEdit.setCompleter(self.searchCompleter)

        self.prevButton = QPushButton('<', clicked=self.handle_backward)
        self.nextButton = QPushButton('>', clicked=self.handle_forward)
        self.textEdit = QTextEdit(readOnly=True)

        hlayout = QHBoxLayout()
        hlayout.setSpacing(0)
        hlayout.setContentsMargins(0 ,0, 0, 0)
        hlayout.addWidget(self.searchLineEdit)
        hlayout.addSpacing(10)
        hlayout.addWidget(self.prevButton)
        hlayout.addWidget(self.nextButton)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(hlayout)
        layout.addWidget(self.textEdit)
        self.hideSearch()
        self.setLayout(layout)

    def append(self, text):
        self.textEdit.append(text)

    def hideSearch(self):
        self.searchLineEdit.setVisible(not self.isHide)
        self.prevButton.setVisible(not self.isHide)
        self.nextButton.setVisible(not self.isHide)
        self.isHide = not self.isHide
        self.update()

    def handle_search(self):
        self.handle_find()

    def handle_forward(self, checked):
        self.handle_find()

    def handle_backward(self, checked):
        self.handle_find(QTextDocument.FindBackward)

    def handle_find(self, findflag=0):
        searchText = self.searchLineEdit.text()
        stringList = self.searchList.stringList()
        stringList.append(searchText)
        self.searchList.setStringList(list(set(stringList)))

        # _ = self.textEdit.find(searchText) if findflag == 0 else self.textEdit.find(searchText, findflag)

        textCurosr = self.textEdit.textCursor()
        document = self.textEdit.document()
        if findflag == 0:
            hi_cursor = document.find(searchText, textCurosr)
            textCurosr.setPosition(hi_cursor.position())
        else:
            hi_cursor = document.find(searchText, textCurosr, findflag)
            textCurosr.setPosition(hi_cursor.anchor() - 1)

        extraSelection = QTextEdit.ExtraSelection()
        extraSelection.cursor = hi_cursor
        extraSelection.format.setBackground(Qt.red)

        self.textEdit.setTextCursor(textCurosr)
        self.textEdit.setExtraSelections([extraSelection])

    def keyPressEvent(self, e):
        if e.modifiers() & Qt.CTRL and e.key() == Qt.Key_F:
            self.hideSearch()

        e.accept()

@mixin.DebugClass
class MonitorWidget(QFrame):
    def __init__(self, dev):
        super().__init__()
        self.dev = dev
        self.buffer = mixin.BytesBuffer()

        self.listWidget = QListWidget()
        self.listWidget.setFixedWidth(80)
        self.listWidget.addItems(['Byte', 'Hex', 'Bin'])

        self.hexEditor = FindTextEdit()
        self.byteEditor = FindTextEdit()
        self.binEditor = FindTextEdit()

        self.stackWidget = QStackedWidget()
        self.stackWidget.addWidget(self.byteEditor)
        self.stackWidget.addWidget(self.hexEditor)
        self.stackWidget.addWidget(self.binEditor)

        layout = QHBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.stackWidget)

        self.listWidget.currentRowChanged.connect(self.stackWidget.setCurrentIndex)
        self.listWidget.setCurrentRow(1)

        self.dev.readSig.connect(self.onReceived)
        self.dev.writeSig.connect(self.onSend)
        self.setLayout(layout)

    def onSend(self, data):
        current_frame = data
        if current_frame:
            bit_frame = BitArray(current_frame)
            hex_data = bit_frame.hex.upper()
            hex_data = [hex_data[i:i + 2] for i in range(0, len(hex_data), 2)]
            hex_data = ' '.join(hex_data)

            byte_data = str(bit_frame.tobytes())
            bin_data = [bit_frame.bin[i:i + 8] for i in range(0, len(bit_frame.bin), 8)]
            bin_data = ' '.join(bin_data)

            self.hexEditor.append('发送：{}'.format(hex_data))
            self.binEditor.append('发送：{}'.format(bin_data))
            self.byteEditor.append('发送：{}'.format(byte_data))

    def onReceived(self, data):
        self.buffer.extend(data)
        current_frame = self.buffer.currentFrame()
        if current_frame:
            bit_frame = BitArray(current_frame)
            hex_data = bit_frame.hex.upper()
            hex_data =  [hex_data[i:i+2] for i in range(0, len(hex_data), 2) ]
            hex_data = ' '.join(hex_data)

            byte_data = str(bit_frame.tobytes())
            bin_data = [bit_frame.bin[i:i+8] for i in range(0, len(bit_frame.bin), 8)]
            bin_data = ' '.join(bin_data)

            self.hexEditor.append('接收：{}'.format(hex_data))
            self.binEditor.append('接收：{}'.format(bin_data))
            self.byteEditor.append('接收：{}'.format(byte_data))

@mixin.DebugClass
class DebugDialog(QDialog):
    prev_actived = False #控制单例
    prev_window = None
    def __init__(self, parent=None, title='数据监听'):
        super().__init__(parent=parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if Config.FIXED_WIN_NUM == 1:
            win = MonitorWidget(Config.RC[0]['dev'])
            layout.addWidget(win)
        elif Config.FIXED_WIN_NUM == 2:
            tabWidget = QTabWidget()
            layout.addWidget(tabWidget)
            for idx in range(Config.FIXED_WIN_NUM):
                dev = Config.RC[idx]['dev']
                page = MonitorWidget(dev)
                tabWidget.addTab(page, dev.name)

        __class__.prev_actived = True
        __class__.prev_window = self
        self.setLayout(layout)
        self.restoreQsetting()

    def restoreQsetting(self):
        geometry = Config.QSETTING.value('MainWindow/DebugDialog/geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        super().closeEvent(event)
        __class__.prev_actived = False
        Config.QSETTING.setValue('MainWindow/DebugDialog/geometry', self.saveGeometry())

#设置对话框
@mixin.DebugClass
class SettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('参数设置')
        self.setWindowFlags(self.windowFlags()&~Qt.WindowContextHelpButtonHint)

        layout = QFormLayout()
        #产品选择combo
        product_list = [item.get('product', '') for item in Config.CONFIG_XML_TREE.findall('//li')]
        product_list = [''] + product_list
        self.product_combo = QComboBox()
        self.product_combo.addItems(product_list)
        self.product_combo.currentIndexChanged[str].connect(self.onProductChoice)
        if Config.PRODUCT_MODEL :
            self.product_combo.setCurrentIndex(self.product_combo.findText(Config.PRODUCT_MODEL))

        #软件版本
        self.software_version = QLineEdit(Config.VERSION, textChanged=self.onVersion)

        #显示方式
        self.show_mode_gb = show_mode_gb = QGroupBox('显示方式:')
        show_mode_layout = QHBoxLayout()
        screen_mode = QRadioButton('分屏显示')
        page_mode = QRadioButton('分页显示')
        screen_mode.toggled.connect(self.onScreenMode)
        page_mode.toggled.connect(self.onPageMode)
        screen_mode.setChecked(True) if Config.SCREEN_MODE else page_mode.setChecked(True)

        show_mode_layout.addWidget(screen_mode)
        show_mode_layout.addWidget(page_mode)
        show_mode_gb.setLayout(show_mode_layout)

        #窗口数量
        win_num_gb = QGroupBox('窗口数量:', toolTip='改变窗口数量后，需重启生效！')
        win_num_layout = QHBoxLayout()
        one_window = QRadioButton('单窗口')
        two_window = QRadioButton('两窗口')
        one_window.toggled.connect(self.onOneWindow)
        two_window.toggled.connect(self.onTwoWindow)
        one_window.setChecked(True) if Config.INITWIN_NUM == 1 else two_window.setChecked(True)
        win_num_layout.addWidget(one_window)
        win_num_layout.addWidget(two_window)
        win_num_gb.setLayout(win_num_layout)

        layout.addRow('产品型号:', self.product_combo)
        layout.addRow('软件版本:', self.software_version)
        layout.addRow(win_num_gb)
        layout.addRow(show_mode_gb)

        self.setLayout(layout)

    def onVersion(self, version):
        Config.VERSION = version

    def onScreenMode(self, checked):
        Config.SCREEN_MODE = checked

    def onPageMode(self, checked):
        Config.SCREEN_MODE = not checked

    def onOneWindow(self, checked):
        Config.INITWIN_NUM = 1
        self.show_mode_gb.setEnabled(False)

    def onTwoWindow(self, checked):
        Config.INITWIN_NUM = 2
        self.show_mode_gb.setEnabled(True)

    def onProductChoice(self, product):
        Config.PRODUCT_MODEL = product
        pathtag = Config.CONFIG_XML_TREE.find('./li[@product="{}"]'.format(product))
        if pathtag is not None:
            xmlpath = pathtag.get('path', '')
            xmlpath = os.path.normpath( os.path.join(Config.APP_DIR, xmlpath) )
            if os.path.exists(xmlpath):
                Config.PRODUCT_XML = xmlpath
                Config.PRODUCT_XML_CHANGED = True
            else:
                QMessageBox.critical(self, '文件', '{} 文件不存在'.format(xmlpath))
                Config.PRODUCT_XML = None
                Config.PRODUCT_XML_CHANGED = False
        else:
            Config.PRODUCT_XML = None
            Config.PRODUCT_XML_CHANGED = False

#串口设置对话框
@mixin.DebugClass
class SerialSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('串口设置')
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QFormLayout()

        self.port_cb = QComboBox()
        self.port_cb.addItems([com.device for com in list_ports.comports()] )
        layout.addRow('端口:', self.port_cb)

        self.baud_cb = QComboBox()
        self.baud_cb.addItems(['9600', '115200'])
        layout.addRow('波特率:', self.baud_cb)

        main_layout = QVBoxLayout()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def getValue(self) -> dict:
        return {'name':self.port_cb.currentText(), 'baudrate':self.baud_cb.currentText() }

#测试单元页面
@mixin.DebugClass
class TestUnitFrame(QFrame):
    def __init__(self, win_idx:int):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setAutoFillBackground(True)

        self.script = QThread()
        self.script.start()
        self.script.quit()

        self.win_idx = win_idx

        #COM Label
        self.com_label = QLabel('COM')
        #状态Label
        self.status_label = QLabel('状态')
        #异常信息
        self.error_label = QLabel('')
        self.error_label.setStyleSheet('.QLabel {color:#A57A80;}')

        leftLayout = QVBoxLayout()
        leftLayout.setSpacing(5)
        leftLayout.addWidget(self.com_label)
        leftLayout.addWidget(self.status_label)
        leftLayout.addWidget(self.error_label)
        leftLayout.addStretch(1)

        ####显示关键信息
        self.productmodel_label = QLabel('')
        self.softversoin_label = QLabel('')
        self.chipid_label = QLabel('')

        #测试按钮
        self.start_button = QPushButton('测试', clicked=self.onUnitTest)
        self.start_button.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.productmodel_label)
        rightLayout.addWidget(self.softversoin_label)
        rightLayout.addWidget(self.chipid_label)

        rightLayout.addStretch(1)
        rightLayout.addWidget(self.start_button)
        rightLayout.setAlignment(self.start_button, Qt.AlignRight)

        #总布局
        mainlayout = QHBoxLayout()
        mainlayout.addLayout(leftLayout)
        mainlayout.addLayout(rightLayout)
        mainlayout.setStretchFactor(leftLayout, 4)
        mainlayout.setStretchFactor(rightLayout, 1)
        self.setLayout(mainlayout)
        self.devInitState()

    def devInitState(self):
        dev = Config.RC[self.win_idx]['dev']
        if dev.status == DevStatus.exception:
            self.com_label.setText('{}[error]'.format(dev.name))
            self.status_label.setText('串口异常')
            self.status_label.setStyleSheet('color: red;')
        elif dev.status == DevStatus.opened:
            self.com_label.setText('{name}[{baudrate}]'.format(**dev.settings))
            self.status_label.setStyleSheet('')
            self.status_label.setText('连接成功')

    def onUnitTest(self, checked):
        dev = Config.RC[self.win_idx]['dev']
        self.error_label.setText('')
        if self.script.isFinished() and dev.status == DevStatus.opened and Config.PRODUCT_XML:
            pub.sendMessage(Config.TOPIC_STARTTEST, win=self)
        elif Config.PRODUCT_XML is None:
            self.status_label.setStyleSheet('color: red;')
            self.status_label.setText('未选择产品型号')
        elif dev.status in [DevStatus.closed, DevStatus.exception]:
            self.status_label.setStyleSheet('color: red;')
            self.status_label.setText('串口未设置')

    def contextMenuEvent(self, event):
        menu = QMenu()
        item = menu.addAction('单元设置')
        menu.addAction('停止测试', self.onStop)
        menu.addAction('串口设置', lambda : self.onSetting(event) )
        menu.addAction('断开串口', self.onDisconnect)
        menu.addAction('重连串口', self.onReconnect)

        item.setEnabled(False)
        menu.move(event.globalPos())
        menu.exec()

    def onStop(self):
        if self.script.isRunning():
            self.script.stop()

    def onSetting(self, event):
        dlg = SerialSettingDialog(self)
        dlg.move(event.globalPos())
        dev = Config.RC[self.win_idx]['dev']
        if dlg.exec():
            settings = dlg.getValue()
            dev.apply_settings(**settings)
            if dev.status == DevStatus.opened:
                dev.close()
            dev.connect()
            if dev.status == DevStatus.exception:
                self.com_label.setText('{}[error]'.format(settings['name']))
                self.status_label.setText('串口异常')
                self.status_label.setStyleSheet('color: red;')
            else:
                self.com_label.setText('{name}[{baudrate}]'.format(**settings))
                self.status_label.setStyleSheet('')
                self.status_label.setText('连接成功')
                if Config.FIXED_WIN_NUM == 2 and not Config.SCREEN_MODE:
                    tab = Config.RC['tab']
                    tab.setCurrentIndex(self.win_idx)
                    tab.setTabText(self.win_idx, settings['name'])

    def onDisconnect(self):
        dev = Config.RC[self.win_idx]['dev']
        if dev.status == DevStatus.opened:
            dev.close()
            self.status_label.setStyleSheet('')
            self.status_label.setText('断开成功')

    def onReconnect(self):
        dev = Config.RC[self.win_idx]['dev']
        if dev.status == DevStatus.closed:
            dev.connect()
            if dev.status == DevStatus.opened:
                self.status_label.setStyleSheet('')
                self.status_label.setText('重连成功')
            else:
                self.status_label.setStyleSheet('color: red;')
                self.status_label.setText('重连失败')

class ResultTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag = ''

#重测按钮
@mixin.DebugClass
class ReTestButton(QWidget):
    def __init__(self, win_idx:int, top_item:ResultTreeWidgetItem):
        super().__init__()
        self.top_item = top_item
        self.win_idx = win_idx

        self.retest_bn = QPushButton(clicked=self.handle_click)
        self.retest_bn.setIcon( self.style().standardIcon(QStyle.SP_MediaPlay) )

        self.step = QThread()
        self.step.start()
        self.step.quit()

        layout = QHBoxLayout()
        layout.setContentsMargins(0 ,0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(self.retest_bn)

        self.setLayout(layout)

    def handle_click(self, checked):
        if self.step.isFinished():
            self.step = step.Step(self.win_idx , self.top_item.tag )
            self.step.sig_item_result.connect(self.handle_item_result)
            self.step.sig_child_item.connect(self.handle_child_item)
            self.step.sig_finish.connect(self.handle_finish)
            self.retest_bn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
            self.top_item.takeChildren()
            self.top_item.setIcon(0, QIcon())
            self.top_item.setText(0, self.top_item.tag)
            self.step.start()
            for idx in range(self.top_item.columnCount()):
                self.top_item.setBackground(idx, Config.COLOR_GRAY)
        elif self.step.isRunning():
            self.step.stop()

    def handle_finish(self, sec):
        origin_text = self.top_item.text(0)
        self.top_item.setText(0, '{} 测试时长:{:.2f}s'.format(origin_text, sec))
        self.retest_bn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def handle_child_item(self, child_item:mix.ChildItem):
        child_widget = QTreeWidgetItem(self.top_item)
        child_widget.setText(0, child_item.tag)
        child_widget.setText(1, child_item.msg)

        if child_item.result:
            bcolor = Config.COLOR_GREEN
            icon = QIcon(Config.PASS_IMG)
        else:
            bcolor = Config.COLOR_RED
            icon = QIcon(Config.FAIL_IMG)

        child_widget.setIcon(0, icon)
        # for i in range(child_widget.columnCount()):
        #     child_widget.setBackground(i, bcolor)

        self.top_item.setExpanded(True)

    def handle_item_result(self, item_result: mix.ItemResult):
        if item_result.result:
            bcolor = Config.COLOR_GREEN
            icon = QIcon(Config.PASS_IMG)
        else:
            bcolor = Config.COLOR_RED
            icon = QIcon(Config.FAIL_IMG)

        self.top_item.setIcon(0, icon)
        self.top_item.setText(0, '{}[{}]'.format(item_result.tag, item_result.total))
        for i in range(self.top_item.columnCount()):
            self.top_item.setBackground(i, bcolor)

#测试结果页面
@mixin.DebugClass
class TestResultFrame(QFrame):
    def __init__(self, win_idx:int):
        super().__init__()
        self.win_idx = win_idx
        self.test_items = []
        self.testunitframe = None #type:TestUnitFrame

        self.tree_widget = QTreeWidget()
        self.tree_widget.setAnimated(True)
        self.tree_widget.setWordWrap(False)
        self.tree_widget.setHeaderLabels(['测试项', '信息'])
        self.tree_widget.setStyleSheet("QTreeView::item { margin: 5px }")

        self.stat_lable = QLabel('')
        self.stat_lable.setAlignment(Qt.AlignRight)
        self.stat_lable.hide()

        pub.subscribe(self.onUnitTest, topicName=Config.TOPIC_STARTTEST)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree_widget)
        layout.addWidget(self.stat_lable)
        self.setLayout(layout)
        self.restoreQSetting()

    def contextMenuEvent(self, event):
        if self.testunitframe and self.testunitframe.script.isFinished():
            menu = QMenu()
            menu.addAction('进入单步', self.onStepIn)
            menu.addAction('退出单步', self.onStepOut)
            menu.addAction('取消异常', self.onOffAlarm)
            menu.exec(event.globalPos())

    def onOffAlarm(self):
        offAlarm = step.OffAlarm(self.win_idx)
        QThreadPool.globalInstance().start(offAlarm)

    def onStepIn(self):
        stepin = step.StepIn(self.win_idx)
        QThreadPool.globalInstance().start(stepin)

    def onStepOut(self):
        stepout = step.StepOut(self.win_idx)
        QThreadPool.globalInstance().start(stepout)

    def onUnitTest(self, win):
        if self.win_idx == win.win_idx:
            self.testunitframe = win  # type:TestUnitFrame

            self.testunitframe.script = Script(self.win_idx)
            pallete = QPalette()
            pallete.setColor(QPalette.Window, Qt.darkCyan)
            self.testunitframe.setPalette(pallete)
            self.testunitframe.status_label.setStyleSheet('')
            self.testunitframe.status_label.setText('正在测试')
            self.testunitframe.start_button.setEnabled(False)

            self.testunitframe.script.sig_item.connect(self.handle_item)
            self.testunitframe.script.sig_item_result.connect(self.handle_item_result)
            self.testunitframe.script.sig_child_item.connect(self.handle_child_item)
            self.testunitframe.script.sig_error.connect(self.handle_error)
            self.testunitframe.script.sig_finish.connect(self.handle_finish)

            #连接关键信息信号
            self.testunitframe.script.sig_model.connect(self.handle_model)
            self.testunitframe.script.sig_sotfversion.connect(self.handle_softversion)
            self.testunitframe.script.sig_chipid.connect(self.handle_chipid)

            #设置关键信息Label
            self.testunitframe.productmodel_label.setText('产品型号:')
            self.testunitframe.softversoin_label.setText('软件版本:')
            self.testunitframe.chipid_label.setText('ChipID:')
            self.testunitframe.softversoin_label.setStyleSheet('')

            #清空状态和测试结果
            self.tree_widget.clear()
            self.test_items.clear()
            self.stat_lable.hide()

            self.testunitframe.script.start()

            if Config.FIXED_WIN_NUM == 2 and not Config.SCREEN_MODE:
                self.parent().parent().setCurrentIndex(self.win_idx)

    def handle_model(self, model):
        origin_text = self.testunitframe.productmodel_label.text()
        self.testunitframe.productmodel_label.setText('{}{}'.format(origin_text, model))

    def handle_softversion(self, version):
        origin_text = self.testunitframe.softversoin_label.text()
        self.testunitframe.softversoin_label.setText('{}{}'.format(origin_text, version))
        if version != Config.VERSION:
            self.testunitframe.softversoin_label.setStyleSheet('color: red;')

    def handle_chipid(self, chipid):
        origin_text = self.testunitframe.chipid_label.text()
        self.testunitframe.chipid_label.setText('{}{}'.format(origin_text, chipid))

    def find_top_item(self, tag: str) -> ResultTreeWidgetItem:
        top_item = None
        items =  self.tree_widget.findItems(tag, Qt.MatchContains, 0)
        for item in items:
            index = self.tree_widget.indexOfTopLevelItem(item)
            if index > -1:
                top_item = item
                break

        return top_item

    def handle_item(self, item: mix.Item):
        self.test_items.append(item.tag)
        if self.test_items.count(item.tag) > 1: return
        topLevelItem = ResultTreeWidgetItem(self.tree_widget)
        topLevelItem.setText(0, item.tag)
        topLevelItem.setText(1, '')
        topLevelItem.tag = item.tag

        self.tree_widget.addTopLevelItem(topLevelItem)

    def handle_item_result(self, item_result:mix.ItemResult):
        if self.test_items.count(item_result.tag) > 1: return
        top_item = self.find_top_item(item_result.tag)

        if item_result.result:
            bcolor = Config.COLOR_GREEN
            icon = QIcon(Config.PASS_IMG)
            top_item.setExpanded(False)
        else:
            bcolor = Config.COLOR_RED
            icon = QIcon(Config.FAIL_IMG)
            top_item.setExpanded(True)

        if 'step' in item_result.flag and item_result.result is False:
            self.tree_widget.setItemWidget(top_item, 1, ReTestButton(self.win_idx, top_item) )

        if top_item:
            top_item.setIcon(0, icon)
            top_item.setText(0, '{} [{}]'.format(top_item.text(0), item_result.total))
            for i in range(top_item.columnCount()):
                top_item.setBackground(i, bcolor)

    def handle_child_item(self, child_item:mix.ChildItem):
        if self.test_items.count(child_item.ptag) > 1: return
        parent_widget = self.find_top_item(child_item.ptag)
        #设置结点数据
        if parent_widget:
            child_widget = ResultTreeWidgetItem(parent_widget)
            child_widget.setText(0, child_item.tag)
            child_widget.setText(1, child_item.msg)

            if child_item.result:
                bcolor = Config.COLOR_GREEN
                icon = QIcon(Config.PASS_IMG)
            else:
                bcolor = Config.COLOR_RED
                icon = QIcon(Config.FAIL_IMG)

            child_widget.setIcon(0, icon)

            # for i in range(child_widget.columnCount()):
            #     child_widget.setBackground(i, bcolor)

            parent_widget.setExpanded(True)
            self.tree_widget.scrollToBottom()

    def handle_error(self, msg):
        msg = '测试异常：' + msg
        self.testunitframe.error_label.setText(msg)

    def handle_finish(self, final_result:mix.FinalResult):
        self.testunitframe.start_button.setEnabled(True)
        self.stat_lable.setText('总时间:{}s'.format(final_result.total_time))
        self.stat_lable.show()

        # 显示结果和颜色
        palette = QPalette()
        if final_result.result:
            palette.setColor(QPalette.Window, Config.COLOR_GREEN)
            self.testunitframe.status_label.setText('PASS')
        else:
            palette.setColor(QPalette.Window, Config.COLOR_RED)
            self.testunitframe.status_label.setText('FAIL')

        self.testunitframe.setPalette(palette)

    def restoreQSetting(self):
        state = Config.QSETTING.value('MainWindow/TestResultFrame/Header/state')
        if state:
            self.tree_widget.header().restoreState(state)

    def __del__(self):
        header = self.tree_widget.header()
        Config.QSETTING.setValue('MainWindow/TestResultFrame/Header/state', header.saveState())

#登录对话框
@mixin.DebugClass
class LoginDialog(QDialog):
    def __init__(self, parent=None, title='登录'):
        super().__init__(parent=parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags()&~(Qt.WindowContextHelpButtonHint|Qt.WindowCloseButtonHint))
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.username = QLineEdit(placeholderText='用户名')
        self.password = QLineEdit(echoMode=QLineEdit.Password, placeholderText='密码')

        layout = QFormLayout()
        layout.setSizeConstraint(QFormLayout.SetFixedSize)
        layout.addRow('用户名:', self.username)
        layout.addRow('密码:', self.password)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addRow(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.setLayout(layout)

@mixin.DebugClass
class TableMsgWidget(QLabel):
    def __init__(self):
        super().__init__()
        icon = self.style().standardIcon(QStyle.SP_FileLinkIcon)
        self.setPixmap(icon.pixmap(icon.actualSize(QSize(16, 16))))
        self.setAlignment(Qt.AlignCenter)

@mixin.DebugClass
class PandasModel(QAbstractTableModel):
    def __init__(self, buf: str):
        super().__init__()
        self.readFromBuf(buf)

    def rowCount(self, parent=None, *args, **kwargs):
        return self._data.index.size

    def columnCount(self, parent=None, *args, **kwargs):
        return self._data.columns.size

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])

        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return QVariant(str(self._data.iat[index.row(), index.column()] ))
        return QVariant()

    def readFromBuf(self, buf):
        csv_buf = io.StringIO()
        csv_buf.write(buf)
        csv_buf.seek(0)
        self._data = pd.read_csv(csv_buf)

@mixin.DebugClass
class TableMsgWidow(QDialog):
    prev_actived = False  # 控制单例
    prev_window = None
    def __init__(self, content: str , title='测试项信息'):
        super().__init__(parent=None)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)
        __class__.prev_actived = True
        __class__.prev_window = self

        self.table = QTableView()
        self.table.horizontalHeader().setHighlightSections(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(True)
        self.restoreQsetting()

        self.table.setModel( PandasModel(content) )

        if QSysInfo.productType() == 'windows' and QSysInfo.productVersion() == '10':
            self.table.horizontalHeader().setStyleSheet("QHeaderView::section { border: 1px solid #D8D8D8; }")

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

    def changeModel(self, content:'csv_string'):
        self.table.setModel(PandasModel(content))

    def closeEvent(self, event):
        super().closeEvent(event)
        __class__.prev_actived = False
        Config.QSETTING.setValue('MainWindow/SearchWindow/MsgWin/Header/state', self.table.horizontalHeader().saveState())
        Config.QSETTING.setValue('MainWindow/SearchWindow/MsgWin/geometry', self.saveGeometry())

    def restoreQsetting(self):
        geometry = Config.QSETTING.value('MainWindow/SearchWindow/MsgWin/geometry')
        header_state = Config.QSETTING.value('MainWindow/SearchWindow/MsgWin/Header/state')
        if geometry:
            self.restoreGeometry(geometry)

        if header_state:
            self.table.horizontalHeader().restoreState(header_state)

#数据记录查询
@mixin.DebugClass
class SearchWindow(QDialog):
    prev_actived = False #控制单例
    prev_window = None
    def __init__(self, parent=None, title='记录查询'):
        super().__init__(parent=parent)
        __class__.prev_actived = True
        __class__.prev_window = self

        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.search_button = QPushButton('查询')
        self.search_button.clicked.connect(self.onSearch)

        header_lables = ['PK', 'ID', '产品', '版本', '芯片ID', '开始时间', '结束时间', '总时间', '结果', '信息']
        self.table = QTableWidget(1, len(header_lables))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(header_lables)
        self.table.horizontalHeader().setHighlightSections(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self.onCellClicked)
        self.table.hideColumn(0)
        self.idx = 0

        if QSysInfo.productType() == 'windows' and QSysInfo.productVersion() == '10':
            self.table.horizontalHeader().setStyleSheet("QHeaderView::section { border: 1px solid #D8D8D8; }")

        layout = QVBoxLayout()
        layout.addWidget(self.search_button)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.restoreQsetting()

    def onCellClicked(self, row, col):
        if col == 9:
            pk_item = self.table.item(row, 0)
            pk = int(pk_item.text())
            q = db.LocalProductionRecord.get_by_id(pk)

            if not TableMsgWidow.prev_actived:
                self.msgwin = TableMsgWidow(q.msg)
                self.msgwin.show()
            else:
                QApplication.setActiveWindow(TableMsgWidow.prev_window)
                TableMsgWidow.prev_window.changeModel(q.msg)

    def onSearch(self, checked:bool):
        query = db.LocalProductionRecord.select()
        self.table.setRowCount(query.count())
        self.idx = 0
        for q in query:
            self.addRow(q)
            self.idx += 1

    def addRow(self, query):
        pk_item = QTableWidgetItem(str(query.id))
        id_item = QTableWidgetItem(str(self.idx + 1))
        model_item = QTableWidgetItem(str(query.model))
        version_item = QTableWidgetItem(str(query.version))
        chipid = QTableWidgetItem(str(query.chipid))
        start_time_item = QTableWidgetItem(mixin.parse_datetime(query.start_time))
        end_time = QTableWidgetItem(mixin.parse_datetime(query.end_time))
        total_time = QTableWidgetItem(str(query.total_time))
        result = QTableWidgetItem(str(query.result))
        msg = TableMsgWidget()

        self.table.setItem(self.idx, 0, pk_item)
        self.table.setItem(self.idx, 1, id_item)
        self.table.setItem(self.idx, 2, model_item)
        self.table.setItem(self.idx, 3, version_item)
        self.table.setItem(self.idx, 4, chipid)
        self.table.setItem(self.idx, 5, start_time_item)
        self.table.setItem(self.idx, 6, end_time)
        self.table.setItem(self.idx, 7, total_time)
        self.table.setItem(self.idx, 8, result)
        self.table.setCellWidget(self.idx, 9, msg)

    def restoreQsetting(self):
        geometry = Config.QSETTING.value('MainWindow/SearchWindow/geometry')
        header_state = Config.QSETTING.value('MainWindow/SearchWindow/Header/state')
        if geometry:
            self.restoreGeometry(geometry)

        if header_state:
            self.table.horizontalHeader().restoreState(header_state)

    def closeEvent(self, event):
        super().closeEvent(event)
        __class__.prev_actived = False
        Config.QSETTING.setValue('MainWindow/SearchWindow/geometry', self.saveGeometry())
        Config.QSETTING.setValue('MainWindow/SearchWindow/Header/state', self.table.horizontalHeader().saveState())

@mixin.DebugClass
class ExceptionWindow(QDialog):
    prev_actived = False #控制单例
    prev_window = None
    def __init__(self, parent=None, title='异常信息'):
        super().__init__(parent=parent)
        __class__.prev_actived = True
        __class__.prev_window = self
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.textEdit = QTextEdit(readOnly=True)
        self.textEdit.setText(Config.DEBUG_HANDLER.getvalue() )

        pub.subscribe(self.onExcption, Config.TOPIC_EXCEPTION)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.textEdit)
        self.setLayout(layout)
        self.restoreQsetting()

    def closeEvent(self, event):
        super().closeEvent(event)
        __class__.prev_actived = False
        Config.QSETTING.setValue('MainWindow/ExceptionWindow/geometry', self.saveGeometry())

    def restoreQsetting(self):
        geometry = Config.QSETTING.value('MainWindow/ExceptionWindow/geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def onExcption(self, triggered):
        self.textEdit.setText(Config.DEBUG_HANDLER.getvalue())

@mixin.DebugClass
class AboutDialog(QDialog):
    def __init__(self, path, parent=None):
        super().__init__()
        self.content = QTextEdit(self, readOnly=True)
        self.content.setHtml(open(path, encoding='utf-8').read())

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok, self)

        self.buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)
        layout.addWidget(self.buttons)
        layout.setSpacing(1)
        self.setLayout(layout)

@mixin.DebugClass
class StepWidget(QFrame):
    def __init__(self, win_idx: int):
        super().__init__()
        self.win_idx = win_idx
        self.tree_widget = QTreeWidget()
        self.tree_widget.setAnimated(True)
        self.tree_widget.setWordWrap(False)
        self.tree_widget.setHeaderLabels(['测试项', '信息'])
        self.tree_widget.setStyleSheet("QTreeView::item { margin: 5px }")

        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.tree_widget)
        self.generate_tree()
        self.setLayout(layout)
        self.restoreQsetting()

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.addAction('进入单步', self.onStepIn)
        menu.addAction('退出单步', self.onStepOut)
        menu.addAction('取消异常', self.onOffAlarm)
        menu.exec(event.globalPos())

    def onOffAlarm(self):
        offAlarm = step.OffAlarm(self.win_idx)
        QThreadPool.globalInstance().start(offAlarm)

    def onStepIn(self):
        stepin = step.StepIn(self.win_idx)
        QThreadPool.globalInstance().start(stepin)

    def onStepOut(self):
        stepout = step.StepOut(self.win_idx)
        QThreadPool.globalInstance().start(stepout)

    def generate_tree(self):
        self.xml = mix.XMLParser()
        for recv_item in self.xml.iter_recv():
            flag = recv_item.get(mix.XMLParser.AFlag, 'general')
            tag = recv_item.get(mix.XMLParser.ATag, '')
            if 'step' in flag:
                top_item = ResultTreeWidgetItem(self.tree_widget)
                top_item.tag = tag
                top_item.setText(0, recv_item.get(mix.XMLParser.ATag, '') )
                top_item.setText(1, '')
                self.tree_widget.setItemWidget(top_item, 1, ReTestButton(self.win_idx, top_item))

    def __del__(self):
        Config.QSETTING.setValue('MainWindow/StepWidget/{}/Header/state'.format(self.win_idx), self.tree_widget.header().saveState())

    def restoreQsetting(self):
        header_state = Config.QSETTING.value('MainWindow/StepWidget/{}/Header/state'.format(self.win_idx))
        if header_state:
            self.tree_widget.header().restoreState(header_state)

@mixin.DebugClass
class SingleStepFrame(QDialog):
    prev_actived = False  # 控制单例
    prev_window = None
    def __init__(self, parent=None, title='单步测试'):
        super().__init__(parent=parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        if Config.FIXED_WIN_NUM == 1:
            layout.addWidget(StepWidget(win_idx=0))
        elif Config.FIXED_WIN_NUM == 2:
            tabWidget = QTabWidget()
            layout.addWidget(tabWidget)
            for idx in range(Config.FIXED_WIN_NUM):
                dev = Config.RC[idx]['dev']
                page = StepWidget(idx)
                tabWidget.addTab(page, dev.name)

        __class__.prev_actived = True
        __class__.prev_window = self
        self.setLayout(layout)
        self.restoreQsetting()

    def closeEvent(self, e):
        super().closeEvent(e)
        __class__.prev_actived = False
        Config.QSETTING.setValue('MainWindow/SingleStepFrame/geometry', self.saveGeometry())

    def restoreQsetting(self):
        geometry = Config.QSETTING.value('MainWindow/SingleStepFrame/geometry')
        if geometry:
            self.restoreGeometry(geometry)