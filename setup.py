from distutils.core import setup
from pymessagefocus import *

setup(name=MessageFocusClient.__module__,
      version=MessageFocusClient.version,
      py_modules=[MessageFocusClient.__module__])
