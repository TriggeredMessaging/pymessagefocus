from distutils.core import setup
import pymessagefocus

setup(name=pymessagefocus.__name__,
      version=pymessagefocus.MessageFocusClient.version,
      packages=[pymessagefocus.__name__])
