# Development

It is important to ensure any pylogix development is compatible with all python version, and micropython. A quick way to check is to run tox, and then run micropython unittests explained in the tests documentation.

# MicroPython quick guide

MicroPython is built for efficiency and thus many sugar functions and entire modules are really short. I would say almost everything can be made to be compatible with MicroPython.

# Setup

I would encourage linux for dev setup, it is a bit more streamlined. You can easily install MicroPython from package manager, or build latest.

My current setup is:
- pycharm with micropython plugin
  - it has integrated repl
  - can upload files from ide
- esptool installed with python2 for flashing esp32 firmware
- screen installed from package manager
- micropython installed from package manager