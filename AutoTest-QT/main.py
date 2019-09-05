import sys
from app.app import MainWindow
from ui import ui
from PyQt5.QtWidgets import QApplication

class App:
    def run(self):
        currentExitCode = MainWindow.EXIT_CODE_REBOOT
        while currentExitCode == MainWindow.EXIT_CODE_REBOOT:
            app = QApplication(sys.argv)
            mainwindow = MainWindow()
            mainwindow.show()
            # self.showLoginDialog(mainwindow)
            currentExitCode = app.exec()
            app = None

    def showLoginDialog(self, mainwindow):
        return ui.LoginDialog(mainwindow).exec()

if __name__ == '__main__':
    app = App()
    app.run()