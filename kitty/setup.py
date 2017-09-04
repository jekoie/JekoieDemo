#coding=utf-8
import sys
from cx_Freeze import setup, Executable

app_name = u'Kitty'
build_exe_options = {
    'include_files':['./img', './logo.jpg', './qus.xml', 'lxml'],
    'excludes': ['tkinter', 'lxml'],
    'optimize': 2
    }

shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     app_name,           # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]Kitty.exe",# Target
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
bdist_msi_options = {'data': msi_data, "upgrade_code": '{9e21d33d-48f7-cf34-33e9-efcfd80eed10}'}

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [Executable(script='main.py', base=base, targetName='Kitty.exe', icon='./kitty.ico')]
setup(name='Kitty',
      author='Chen Jie',
      version='1.0',
      description='A app for a pretty girl ^^',
      options={'build_exe': build_exe_options, 'bdist_msi': bdist_msi_options},
      executables = executables,
      )