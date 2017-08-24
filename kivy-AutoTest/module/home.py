import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.splitter import Splitter
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.lang.builder import Builder
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.app import runTouchApp
from kivy.factory import Factory
import kivy

dirpath =  os.path.normpath( os.path.dirname(__file__) )
kivypath = os.path.join(dirpath, 'home.kv'  )
Builder.load_file( kivypath )

Factory.register('Tabbedpanel', cls=kivy.uix.tabbedpanel.TabbedPanel)
class COMTabbedpanel(TabbedPanel):
    pass

class Home(BoxLayout):
    pass

