from cx_Freeze import setup, Executable
import sys

sys.setrecursionlimit(5000)
# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {'packages': ['requests_ntlm', 'spnego'], 'excludes': []}

base = 'console'

executables = [
    Executable('run_app.py', base=base, target_name = 'My app', icon='media/icon.ico')
]

setup(name='my_app',
      version = '1.0',
      description = 'My app',
      options = {'build_exe': build_options},
      executables = executables)
