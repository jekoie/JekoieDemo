import sys
from app.app import MainWindow
from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    currentExitCode = MainWindow.EXIT_CODE_REBOOT
    while currentExitCode == MainWindow.EXIT_CODE_REBOOT:
        app = QApplication(sys.argv)
        mainwindow = MainWindow()
        mainwindow.show()
        currentExitCode = app.exec()
        app = None

