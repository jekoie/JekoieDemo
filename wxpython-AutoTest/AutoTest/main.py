import wx
from app import app

class App(wx.App):
    def __init__(self):
        wx.App.__init__(self)

    def OnInit(self):
        app.main()
        return True

if __name__ == '__main__':
    App()

