import sys
from config.config import Config
from cx_Freeze import setup, Executable

app_name = 'AutoTest'
app_uuid = '{9f21d33d-48f7-cf34-33e9-afcfd80eed11}'

build_exe_options = {
    'include_files': ['./app' ,'./communicate', './config', './image', './product', './script', './setting',
                      './tmp', './ui'],
    'packages':['pandas', 'numpy', 'faker'],
    'excludes':['IPython', 'jupyter_client', 'ipykernel', 'jedi', 'jinjia2', 'jupyter_core', 'nbconvert',
                'ipython_genutils', 'nbformat', 'notebook'],
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

executables = [Executable(script='main.py', base=base, targetName='{}.exe'.format(app_name))]
setup(name='{}'.format(app_name),
      author='Chen Jie',
      version=Config.APP_VERSION,
      description='ShenZhen bona company factory autotest tool',
      options={'build_exe': build_exe_options, 'bdist_msi': bdist_msi_options},
      executables = executables,
      )