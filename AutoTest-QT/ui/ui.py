import os
import pandas as pd
from communicate.communicate import DevStatus
from config.config import Config
from PyQt5.QtCore import Qt, QThread, QSysInfo
from PyQt5.QtWidgets import (QDialog, QFormLayout, QComboBox, QGroupBox, QHBoxLayout, QRadioButton,QVBoxLayout, QFileDialog,
                             QDialogButtonBox, QFrame, QLabel, QPushButton, QMenu, QTableWidget, QHeaderView, QTabWidget,
                             QAbstractItemView, QTableWidgetItem, QMessageBox, QTextEdit, QListWidget, QStackedWidget)
from PyQt5.QtGui import QPalette, QColor, QIcon
from serial.tools import list_ports
from script.script import Script
from bitstring import BitArray
from ui import mixin
from pubsub import pub
import traceback

class MonitorWidget(QFrame):
    def __init__(self, dev):
        super().__init__()
        self.dev = dev
        self.buffer = mixin.BytesBuffer(b'\xff')

        self.listWidget = QListWidget()
        self.listWidget.setFixedWidth(80)
        self.listWidget.addItems(['Byte', 'Hex', 'Bin'])

        self.hexEditor = QTextEdit(readOnly=True)
        self.byteEditor = QTextEdit(readOnly=True)
        self.binEditor = QTextEdit(readOnly=True)

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

        self.dev.transmited.connect(self.onReceived)
        self.setLayout(layout)

    def onReceived(self, data):
        self.buffer.extend(data)
        current_frame = self.buffer.currentFrame
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

class DebugDialog(QDialog):
    prev_actived = False #控制单例
    prev_window = None
    def __init__(self, parent=None, title='数据监视'):
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
        layout.addRow(win_num_gb)
        layout.addRow(show_mode_gb)

        self.setLayout(layout)

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
class TestUnitFrame(QFrame):
    def __init__(self, win_idx:int):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setAutoFillBackground(True)

        self.script = QThread()
        self.script.start()
        self.script.quit()

        self.win_idx = win_idx

        #COM Label布局
        self.com_label = QLabel('COM')
        com_layout = QHBoxLayout()
        com_layout.addWidget(self.com_label)

        #状态Label布局
        self.status_label = QLabel('状态')
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)

        #测试按钮布局
        self.start_button = QPushButton('测试')
        self.start_button.clicked.connect(self.onUnitTest)

        hlayout = QHBoxLayout()
        hlayout.addStretch(1)
        hlayout.addWidget(self.start_button)

        #总布局
        vlayout = QVBoxLayout()
        vlayout.addLayout(com_layout)
        vlayout.addLayout(status_layout)
        vlayout.addStretch(1)
        vlayout.addLayout(hlayout)
        self.setLayout(vlayout)
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
        if self.script.isFinished() and dev.status == DevStatus.opened and Config.PRODUCT_XML:
            self.script = Script(dev, self.win_idx)
            pallete = QPalette()
            pallete.setColor(QPalette.Window, Qt.darkCyan)
            self.setPalette(pallete)
            self.status_label.setStyleSheet('')
            self.status_label.setText('正在测试')
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
        menu.addAction('停止', self.onStop)
        menu.addAction('设置', lambda : self.onSetting(event) )
        menu.addAction('断开连接', self.onDisconnect)
        menu.addAction('重新连接', self.onReconnect)
        menu.addAction('结果导出', self.onExportResult)

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
            try:
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
                    if Config.INITWIN_NUM == 2 and not Config.SCREEN_MODE:
                        tab = Config.RC['tab']
                        tab.setCurrentIndex(self.win_idx)
                        tab.setTabText(self.win_idx, settings['name'])
            except Exception as e:
                import traceback
                print(traceback.format_exc())

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

    def onExportResult(self):
        result = Config.RC[self.win_idx].get('result', None)
        result_list = Config.RC[self.win_idx].get('result_list', None)
        if result and result_list:
            filename = QFileDialog.getSaveFileName(self, '另存为', filter='Excel (*.xlsx)')[0]
            if filename:
                df = pd.DataFrame(result_list, columns=['测试项', '信息', '结果'])
                df = df.replace([True, False], ['PASS', 'FAIL'])
                df.to_excel(filename)

#测试结果页面
class TestResultFrame(QFrame):
    def __init__(self, win_idx:int):
        super().__init__()
        self.table_current_idx = 0
        self.pass_item_count = 0
        self.fail_item_count = 0
        self.win_idx = win_idx
        self.table_default_row = 1
        self.table_default_col = 4
        self.testunitframe = None
        self.result_list = []

        self.table = QTableWidget(self.table_default_row, self.table_default_col)
        self.table.hideColumn(self.table_default_col - 1)
        self.table.setHorizontalHeaderLabels(['ID', '测试项', '信息'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setHighlightSections(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.resizeRowsToContents()

        if QSysInfo.productType() == 'windows' and QSysInfo.productVersion() == '10':
            self.table.horizontalHeader().setStyleSheet( "QHeaderView::section { border: 1px solid #D8D8D8; }")

        self.stat_lable = QLabel('')
        self.stat_lable.setAlignment(Qt.AlignRight)
        self.stat_lable.hide()
        pub.subscribe(self.onUnitTest, topicName=Config.TOPIC_STARTTEST)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        layout.addWidget(self.stat_lable)
        self.setLayout(layout)

    def onUnitTest(self, win):
        if self.win_idx == win.win_idx:
            self.table_current_idx = 0
            self.pass_item_count = 0
            self.fail_item_count = 0
            self.testunitframe = win
            self.testunitframe.setStyleSheet('')
            self.stat_lable.hide()
            self.result_list.clear()
            self.table.setRowCount(0)
            self.testunitframe.script.sig_finish.connect(self.threadFinish)
            self.testunitframe.script.sig_data.connect(self.recvThreadData)
            self.testunitframe.script.start()
            if Config.INITWIN_NUM == 2 and not Config.SCREEN_MODE:
                self.parent().parent().setCurrentIndex(self.win_idx)

    def threadFinish(self, result):
        self.stat_lable.setText('总测试项:{} PASS项:{} FAIL项:{}'.format(self.table_current_idx, self.pass_item_count, self.fail_item_count))
        self.table.setRowCount(self.table_current_idx)
        self.table.sortByColumn(3, Qt.AscendingOrder)
        self.stat_lable.show()
        self.table.scrollToTop()

        #显示结果和颜色
        palette = QPalette()
        if result:
            palette.setColor(QPalette.Window, Qt.green)
            self.testunitframe.status_label.setText('PASS')
            Config.RC[self.win_idx].update({'result':'PASS', 'result_list': self.result_list})
        else:
            palette.setColor(QPalette.Window, Qt.red)
            self.testunitframe.status_label.setText('FAIL')
            Config.RC[self.win_idx].update({'result': 'FAIL', 'result_list': self.result_list})

        self.testunitframe.setPalette(palette)

    def recvThreadData(self, data):
        self.result_list.append(data)
        #行数不够，新增一行
        if self.table_current_idx > self.table.rowCount() - 1:
            self.table.insertRow(self.table_current_idx)

        #添加数据项
        index_item = QTableWidgetItem(str(self.table_current_idx + 1))
        self.table.setItem(self.table_current_idx, 0, index_item)
        self.table.setItem(self.table_current_idx, 1, QTableWidgetItem(data[0]) )
        self.table.setItem(self.table_current_idx, 2, QTableWidgetItem(data[1]) )

        if data[2]:
            self.table.setItem(self.table_current_idx, 3, QTableWidgetItem('1'))
            index_item.setIcon(QIcon(Config.PASS_IMG))
            self.setRowColor(self.table_current_idx, Qt.green)
            self.pass_item_count += 1
        else:
            self.table.setItem(self.table_current_idx, 3, QTableWidgetItem('0'))
            index_item.setIcon(QIcon(Config.FAIL_IMG))
            self.setRowColor(self.table_current_idx, Qt.red)
            self.fail_item_count += 1

        self.table.scrollToBottom()
        self.table_current_idx += 1

    def setRowColor(self, row:int, color:QColor):
        for col in range(self.table.columnCount()):
            self.table.item(row, col).setBackground(color)