#coding=utf-8
import sys
import os
import shutil
from config.config import Config
from cx_Freeze import setup, Executable
from ui import tool

############################单串口版##############################
def clear():
    try:
        Config.genfilepath(os.getcwd())
        with tool.AppSettingReader() as s:
            s.set('wnpasswd', {'value': '' })
            s.set('mode', {'value': 'single'})
            s.set('protocol', {'value': 'serial'})
            s.set('initwinnum', {'value': '1'})

        if os.path.exists(Config.tmp):
            shutil.rmtree(Config.tmp)
        os.mkdir(Config.tmp)
    except Exception:
        pass

clear()
app_name = 'AutoTest2'
app_uuid = '{9f21d33d-48f7-cf34-33e9-efcfd80eed11}'

build_exe_options = {
    'include_files': ['./app' ,'./communicate', './config', './db', './doc', './image', './oracle',
                      './product', './setting', './ui', './tool', './exe', './instrument', './tmp'],
    'packages':['pyftpdlib', 'xlwt' ,'pkg_resources' ,'ftfy', 'lxml', 'numpy' ,'pandas'],
    'excludes': ['sqlalchemy','Tkinter', 'matplotlib', 'scrapy', 'IPython', 'cffi', 'colorama', 'httpie',
                 'jupyter', 'splinter', 'openpyxl', 'flasky','test', 'jinja2', 'setuptools'],
    'include_msvcr': True,
    }


shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     app_name,           # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]{}.exe".format(app_name),# Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
     ),
    #
    # ("StartupShortcut",           # Shortcut
    #  "MenuDir",                   # Directory_
    #  app_name,                # Name
    #  "TARGETDIR",                 # Component_
    #  "[TARGETDIR]AutoTest.exe",   # Target
    #  None,                        # Arguments
    #  None,                # Description
    #  None,                        # Hotkey
    #  None,                        # Icon
    #  None,                        # IconIndex
    #  None,                        # ShowCmd
    #  'TARGETDIR'                  # WkDir
    #  ),

    # ("UniShortcut",  # Shortcut
    #  "MenuDir",  # Directory_
    #  unapp_name,  # Name
    #  "TARGETDIR",  # Component_
    #  "[System64Folder]msiexec.exe",  # Target
    #  r"/x" + msilib.gen_uuid(),  # Arguments
    #  'how are you',  # Description
    #  None,  # Hotkey
    #  None,  # Icon
    #  None,  # IconIndex
    #  None,  # ShowCmd
    #  'TARGETDIR'  # WkDir
    #  )
    ]

# Now create the table dictionary
msi_data = {"Shortcut": shortcut_table}

# Change some default MSI options and specify the use of the above defined tables
bdist_msi_options = {'data': msi_data, "upgrade_code":  app_uuid}

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [Executable(script='main.py', base=base, targetName='{}.exe'.format(app_name), icon='./image/panda.ico')]
setup(name='{}'.format(app_name),
      author='Chen Jie',
      version=Config.__version__,
      description='ShenZhen Raisecom company factory autotest tool',
      options={'build_exe': build_exe_options, 'bdist_msi': bdist_msi_options},
      executables = executables,
      )

