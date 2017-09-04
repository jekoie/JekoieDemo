#coding:utf-8
import os
import signal
import wx
import sys
import wx.adv
import random
import platform
import arrow
import threading
import socket
from pathlib2 import Path
from envelopes import Envelope, SMTP
from lxml import etree
from collections import OrderedDict
from StringIO import StringIO
from wx.adv import Wizard, WizardPageSimple
reload(sys)
sys.setdefaultencoding('utf-8')
IMG_PATH = 'img'

class EMAIL(object):
    def __init__(self):
        self.smtp = SMTP('host, login='username', password='passwd', tls=True)

    def Send(self, content=''):
        envelop = Envelope(
            from_addr=(u'aa@com', u'name'),
            to_addr=( u'bb@com', 'bb'),
            subject=u'Hello Kitty, That all for you',
            text_body=content
        )
        self.smtp.send(envelop)

class Scene(WizardPageSimple):
    def __init__(self, parent=None, node=None, record=None, img=None):
        WizardPageSimple.__init__(self, parent=parent)
        self.img = img
        self.node, self.record = node, record
        self.issue_qustion = issue_qustion = node.get('name')
        self.answer = int( node.get('answer') ) - 1
        self.issue_qustion_list = issue_qustion_list = [ node_child.get('choice') for node_child in node.iterchildren()]
        issue = wx.StaticText(self, label=issue_qustion)
        self.issue_list = issue_list = wx.RadioBox(self, choices=issue_qustion_list, majorDimension=1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(issue, wx.SizerFlags().Expand())
        sizer.Add(issue_list, 1, wx.EXPAND)

        issue_list.Bind(wx.EVT_RADIOBOX, self.OnRadioSelect)
        self.SetSizer(sizer)
        self.SetBackgroundStyle(wx.BG_STYLE_ERASE)
     #   self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnRadioSelect(self, evt):
        pass

    def OnEraseBackground(self, evt):
        dc = evt.GetDC()
        rect = None
        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
        dc.Clear()

        img = wx.Image('img/kitty.jpg')
      #  img.Rescale(dc.GetSize()[0], dc.GetSize()[1])
        bmp = img.ConvertToBitmap()
        dc.DrawBitmap(bmp, 0, 0, True)

    def GetBitmap(self):
        img = wx.Image(self.img)
        img =  img.Rescale(200, 300)
        return wx.Bitmap(img)

class WizardQuestion(Wizard):
    def __init__(self, parent=None):
        Wizard.__init__(self, parent = parent, title='Hello Kitty', bitmap=wx.Bitmap('img/kitty.jpg'))
        self.SetPageSize((400, 200))
        self.SetIcon(wx.Icon('logo.jpg') )
        root = etree.parse('qus.xml').getroot()
        firstpage = None
        self.pool = OrderedDict()
        img_list = [ path.as_posix()  for path in  Path(IMG_PATH).glob('*.jpg')]
        for node in root.xpath('.//question'):
            img = img_list[random.randint(0, len(img_list) - 1) ]
            if firstpage == None:
                firstpage = page = Scene(self, node, img=img)
            else:
                page = page.Chain(Scene(self, node, img=img))

        self.Bind(wx.adv.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.adv.EVT_WIZARD_CANCEL, self.OnWizardCancel)
        self.Bind(wx.adv.EVT_WIZARD_FINISHED, self.OnWizardFinished)
        self.start_time = arrow.now()
        self.RunWizard(firstpage)


    def OnPageChanged(self, evt):
        current_page = evt.GetPage()
        prev_page = current_page.GetPrev()
        if prev_page:
            # print prev_page.issue_qustion
            # print prev_page.issue_list.GetString( prev_page.issue_list.GetSelection() )
            # print prev_page.issue_qustion_list[prev_page.answer]
            self.pool[prev_page.issue_qustion] = {'your': prev_page.issue_list.GetString( prev_page.issue_list.GetSelection() ),
                                                  'right':  prev_page.issue_qustion_list[prev_page.answer]
                                                  }
    def OnWizardCancel(self, evt):
        wx.MessageBox(u'好吧，怎么没答完啊，答完后面有惊喜哦', 'Hello Kitty')

    def OnWizardFinished(self, evt):
        self.end_time = arrow.now()
        page = evt.GetPage()
        self.pool[page.issue_qustion] = {
            'your': page.issue_list.GetString(page.issue_list.GetSelection()),
            'right': page.issue_qustion_list[page.answer]
            }
        content = ''
        right_count = 0
        for qus, ans in self.pool.iteritems():
            content += qus + '\n'
            content += '    Your answer: ' + ans['your'] + '\n'
            content += '    Right answer: ' + ans['right'] + '\n'
            if ans['your'] == ans['right']:
                right_count += 1

        msg = ''
        msg += '开始时间：{}    结束时间：{}   用户:{}    IP:{} 正确比例:{}/{}\n'.format(self.start_time.format('YYYY-MM-DD HH:mm:ss'),
                                                              self.end_time.format('YYYY-MM-DD HH:mm:ss'), platform.node(),
                                                              socket.gethostbyname(socket.gethostname()), right_count, len(self.pool))
        msg += '系统:{}{} {} CPU:{} machine:{}\n'.format(platform.system(), platform.release(), platform.version(),
                                                       platform.processor(), platform.machine())
        content = msg + content
        content += u'Author:陈杰\n'
        try:
            email = EMAIL()
            email.Send(content)
        except Exception as e:
            pass
        wx.MessageBox(u'恭喜完成到最后，我给你发个打红包了哦，嘿嘿！', 'Hello Kitty')
        wx.MessageBox(u'如果你电脑联网了的话，我现在给你发邮件了，快到QQ邮箱里看看吧，没有找到的话，就在垃圾箱里了！', 'Hello Kitty')
        wx.MessageBox(u'哎呀， 你的电脑10s内要重启了, 在关闭窗口前， 保存好文件， 55555555！', 'Hello Kitty')
        def shutdown():
            os.system('shutdown /r /s /t 10')
        threading.Thread(target=shutdown).start()

app = wx.App()
WizardQuestion()
app.MainLoop()
os.kill(os.getpgid(), signal.SIGABRT)
