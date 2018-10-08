#coding=utf-8
import sys
import os
from app import __version__
from cx_Freeze import setup, Executable

############################单串口版##############################

official_version = True
if official_version:
    app_name = 'AutoTest'
    app_uuid = '{9f21d33d-48f7-cf34-33e9-efcfd80eed10}'
else:
    app_name = 'AutoTest_beta'
    app_uuid = '{9f21d33d-48f7-cf34-33e9-efcfd80eed11}'

basedir = os.path.dirname( os.path.abspath(__file__) )
settingdir = os.path.join(basedir, 'setting')
for file in os.listdir(settingdir):
    os.remove(os.path.join(settingdir, file))

build_exe_options = {
    'include_files': ['./app' ,'./tool', './image', './doc', './setting'],
    'packages':['pyftpdlib', 'xlwt' ,'pkg_resources' ,'ftfy', 'lxml', 'numpy' ,'pandas'],
    'excludes': ['sqlalchemy','Tkinter', 'matplotlib', 'scrapy', 'IPython', 'cffi', 'colorama', 'httpie',
                 'jupyter', 'splinter', 'openpyxl', 'flasky''test', 'jinja2', 'multiprocessing', 'win32process',
                 'win32api', 'win32file', 'setuptools'],
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


executables = [Executable(script='main.py', base=base, targetName='{}.exe'.format(app_name), icon='./image/logo.ico')]
setup(name='{}'.format(app_name),
      author='Chen Jie',
      version=__version__,
      description='ShenZhen Raisecom company factory autotest tool',
      options={'build_exe': build_exe_options, 'bdist_msi': bdist_msi_options},
      executables = executables,
      )

