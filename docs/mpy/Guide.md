# Install Pylogix to a board running MicroPython

Before you can use pylogix on your board, you have to flash it with the correct firmware. For development purposes I went with ESP32, and raspberry pico since they are widely available and relatively low cost. I suggest to stick to these two at least for now, use other models at your own risk.

There are dozens if not hundreds of supported boards, some will have too little system resources to support pylogix so be aware of those limitation.

Checkout the official documentation to install MicroPython 1.20+, once you get a repl, return to this document. If your board has wifi onboard ensure you install the correct firmware, some boards have different firmware based on the hardware to make firmware smaller.

https://docs.micropython.org/en/latest/
https://docs.micropython.org/en/latest/esp32/tutorial/intro.html#esp32-intro

> NB: esptool only works with python 2.7, so ensure python 2.7 is installed on your system in order to flash the binary to the esp32.

https://www.raspberrypi.com/documentation/microcontrollers/micropython.html

> NB: We will not support issues with getting your board flashed with micropython, so please seek help in the respective board forums.

# Running py files

You can run commands, and scripts with [pyboard.py](https://docs.micropython.org/en/latest/reference/pyboard.py.html). I also recommend using mu, or thonny editors if you are a beginner they both support micropython. I use jetbrains pycharm which has a plugin for micropython, although in latest editions the repl seems to be broken.

In short micropython has two files which are treated special, boot.py and main.py. If these files exist, boot loads when the device boots, here in the example I created some utility functions to either connect to LAN or WAN, and at the bottom of the file you can specify which functions run automatically. The main.py file runs after boot, and will continue to run until you enter a REPL.

> NB: There are tons of micropython tutorials out there, same as before micropython support is only scoped to pylogix for issues running files and uploading seek help in the respective forums.

# Installing pylogix with internet boards

Once you have a repl, and know how to upload files to your board checkout the directory under examples called 01_micropython_example. If you intend to use wifi, enter your ssid and password in the connect_wan() function. In the main.py file, change the ip to your PLC, and configure your tags accordingly. Then upload both files to the board. Launch the repl and type the following lines.

```python
import mip
mip.install("github:dmroeder/pylogix")
```
In the repl, you can run ls() which is a function I've loaded in the boot.py

```
MicroPython v1.20.0 on 2023-04-26; Raspberry Pi Pico W with RP2040
Type "help()" for more information.
>>> ls
<function ls at 0x20012620>
>>> ls()
['boot.py', 'lib', 'main.py']
>>> ls("lib")
['pylogix']
>>> ls("lib/pylogix")
['__init__.mpy', 'eip.mpy', 'lgx_comm.mpy', 'lgx_device.mpy', 'lgx_response.mpy', 'lgx_tag.mpy', 'lgx_uvendors.mpy.bin', 'lgx_uvendors.mpy', 'utils.mpy', 'vendors.bin']
```

# Installing pylogix without internet

In a pycharm project, create a directory called lib, then inside lib, another called pylogix. `[root]/lib/pylogix`. Inside the pylogix dir, copy all files from upylogix from the repository. Then flash lib dir to the device. Then flash main.py and boot.py, when the devices reboot, it should change whatever tags you've configured in the PLC.