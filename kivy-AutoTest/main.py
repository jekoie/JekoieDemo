#coding:utf-8
import sys
import kivy
import json
from kivy.app import App, runTouchApp
from kivy.uix.button import Button
from kivy.uix.label import Label
from serial.tools.list_ports import comports
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.lang.builder import Builder
from kivy.uix.settings import *
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import Screen, ScreenManager
from module.home import Home

reload(sys)
sys.setdefaultencoding('utf-8')
kivy.resources.resource_add_path('./font')
chiness_font=kivy.resources.resource_find('simsun.ttc')
LabelBase.font_name = chiness_font
LabelBase.register('simsun', fn_regular='./font/simsun.ttc', fn_bold=chiness_font, fn_italic=chiness_font)

class MainScreen(BoxLayout):
    sm = ObjectProperty(None, allownone=True)
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

class AutoApp(App):
    settings_cls =  SettingsWithTabbedPanel
    def build_config(self, config):
        com_option = {'baudrate': 9600, 'bytesize':8, 'parity' : 'N','stopbits': 1,'timeout' :1, 'write_timeout': 0}
        for com in comports():
            config.setdefaults(str(com.device), com_option)


    def build_settings(self, settings):
        data = [
            {"type": "title", "title": u'' },
            {"type": "options", "title": "波特率", "desc": "baudrate", "section": '', "key": "baudrate", "options": ["9600", "115200"]},
            {"type": "options", "title": "bytesize", "desc": "bytesize", "section": '', "key": "bytesize", "options": ["5", "6", "7", "8"]},
            {"type": "options", "title": "parity", "desc": "parity", "section": '', "key": "parity", "options": ["N", "E", "O", "S", "M"]},
            {"type": "options", "title": "stopbits", "desc": "stopbits", "section": '', "key": "stopbits", "options": ["1", "2"]},
            {"type": "numeric", "title": "timeout", "desc": "timeout", "section": '', "key": "timeout"},
            {"type": "numeric", "title": "write_timeout", "desc": "write_timeout", "section": '', "key": "write_timeout"} ]

        for com in comports():
            for item in data:
                if item['type'] == 'title':
                    item['title'] = str(com.device)
                else:
                    item['section'] = str(com.device)
            settings.add_json_panel(str(com.device), self.config, data=json.dumps(data))

    def build(self):
        self.root = MainScreen()
        screen_item = [('home', Home() ), ('log', Button(text='log') ), ('database', Button(text='db'))  ]
        for name, widget in screen_item:
            screen = Screen(name=name)
            screen.add_widget(widget)
            self.root.sm.add_widget(screen)

Builder.load_file('main.kv')
AutoApp().run()