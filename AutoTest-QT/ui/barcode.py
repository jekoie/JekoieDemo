from PyQt5.QtWidgets import QWidget, QDialog, QGridLayout, QPushButton, QLineEdit, QTabWidget, QLabel, QVBoxLayout, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintDialog
from config.config import Config
import barcode
import qrcode
import os
from barcode.writer import ImageWriter
from ui.mixin import DebugClass

class Base(QWidget):
    def __init__(self):
        super().__init__()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.preview_label)
        self.setLayout(layout)

    def set(self, content):pass

    def save(self, filename):pass

@DebugClass
class BarcodeWiget(Base):
    def __init__(self, content='BL01648'):
        super().__init__()
        self.bc = barcode.get('code128', content, ImageWriter())
        self.preview_label.setPixmap(self.bc.render(self.option).toqpixmap())

    def set(self, content):
        self.bc = barcode.get('code128', content, ImageWriter())
        self.preview_label.setPixmap(self.bc.render(self.option).toqpixmap())

    def save(self, filename):
        filename = os.path.splitext(filename)[0]
        self.bc.save(filename, self.option)

    @property
    def option(self):
        return  {
        'module_width': 0.2,
        'module_height': 10.0,
        'quiet_zone': 1,
        'font_size': 8,
        'text_distance': 1.0,
        'background': 'white',
        'foreground': 'black',
        'write_text': True,
        'text': ''}

class QRCodeWidget(Base):
    def __init__(self, content='wxp://f2f0z7PHJ3rnH7GjfiUZTeJP90a_AG4_iFrx'):
        super().__init__()
        self.qrcode = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4 )
        self.qrcode.add_data(content)
        self.qrcode.make()

        img = self.qrcode.make_image().get_image()
        self.preview_label.setPixmap(img.toqpixmap())

    def set(self, content):
        self.qrcode.clear()
        self.qrcode.add_data(content)
        self.qrcode.make()

        img = self.qrcode.make_image().get_image()
        self.preview_label.setPixmap(img.toqpixmap())

    def save(self, filename):
        self.qrcode.make_image().save(filename, format='png')

@DebugClass
class CodeDialog(QDialog):
    prev_actived = False #控制单例
    prev_window = None
    def __init__(self, parent=None, title='条码生成器'):
        super().__init__(parent=parent)
        __class__.prev_actived = True
        __class__.prev_window = self
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(title)

        self.tabWiget = QTabWidget()
        self.lineEdit = QLineEdit(placeholderText='在这里输入内容')
        self.generate_button = QPushButton('生成', released=self.handle_generate)
        self.printpeview_button = QPushButton('打印预览', released=self.handle_preview)
        self.save_button = QPushButton('保存', released=self.handle_save)

        self.tabWiget.addTab(BarcodeWiget(), '条形码')
        self.tabWiget.addTab(QRCodeWidget(), '二维码')

        layout = QGridLayout()
        layout.addWidget(self.tabWiget, 0, 0, 1, 3)
        layout.addWidget(self.lineEdit, 1, 0, 1, 3)
        layout.addWidget(self.generate_button, 2, 0)
        layout.addWidget(self.printpeview_button, 2, 1)
        layout.addWidget(self.save_button, 2, 2)
        self.setLayout(layout)
        self.restoreQsetting()

    def closeEvent(self, event):
        super().closeEvent(event)
        __class__.prev_actived = False
        Config.QSETTING.setValue('MainWindow/CodeWindow/geometry', self.saveGeometry())

    def restoreQsetting(self):
        geometry = Config.QSETTING.value('MainWindow/CodeWindow/geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def handle_generate(self):
        if self.lineEdit.text():
            code_widget = self.tabWiget.currentWidget()
            code_widget.set(self.lineEdit.text())

    def handle_preview(self):
        preview = QPrintPreviewDialog()
        preview.paintRequested.connect(self.handle_paint)
        preview.exec()

    def handle_save(self):
        self.tabWiget.currentWidget().grab()

        filename = QFileDialog.getSaveFileName(self, '保存文件', filter='PNG File (*.png)')[0]
        if filename:
            self.tabWiget.currentWidget().save(filename)


    def handle_paint(self, printer):
        painter = QPainter(printer)
        painter.begin(printer)
        self.tabWiget.currentWidget().render(painter)
        painter.end()