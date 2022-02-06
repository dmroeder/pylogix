# pylogix

pylogix is a communication driver that lets you easily read/write values from tags in Rockwell Automation ControlLogix, CompactLogix and Micro8xx PLC's over Ethernet I/P using Python.  Only PLC's that are programmed with RSLogix5000/Studio5000 or Connected Components Workbench (Micro8xx), models like PLC5, SLC, MicroLogix are *not* supported.  They use a different protocol, which I have no plans to support.

There are many devices that support CIP objects that allow for automatic disocvery (like RSLinx does), which pylogix can discover, but will likely not be able to interact with in any other meaningful way.  Pylogix is really only intended to talk to the above mentioned PLC's and is only tested against them.  It likely will not communicate with any other brands.

For general support or questions, I created a [discord](https://discord.gg/tw8E9EAAnf), feel free to join and ask questions, I'll do my best to help in a timely manner.

## Getting Started

There are currently no dependencies so you can get going quickly without having to install any other prerequiste packages.  Both python2 and python3 are supported.

### Installing

Install pylogix with pip (Latest version):

```console
pylogix@pylogix-kde:~$ pip install pylogix
```

To install previous version before major changes (0.3.7):

```console
pylogix@pylogix-kde:~$ pip install pylogix==0.3.7
```

To upgrade to the latest version:

```console
pylogix@pylogix-kde:~$ pip install pylogix --upgrade
```

Alternatively, you can clone the repo and manually install it:

```console
pylogix@pylogix-kde:~$ git clone https://github.com/dmroeder/pylogix.git
pylogix@pylogix-kde:~$ cd pylogix
pylogix@pylogix-kde:~/pylogix$ python setup.py install --user
```

### Verifying Installation

To verify the installation on Linux, open the terminal and use the following commands:

```console
pylogix@pylogix-kde:~$ python3
Python 3.8.5 (default, Jan 27 2021, 15:41:15) 
[GCC 9.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import pylogix
>>> pylogix.__version__
'0.7.10'
```

### Your First Script:

The cloned repository will come with many examples, I'll give one here.  We'll read one simple tag and print out the value.  All methods will return the Response class, which contains TagName, Value and Status.

```python
from pylogix import PLC
with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    ret = comm.Read('MyTagName')
    print(ret.TagName, ret.Value, ret.Status)
```

NOTE: If your PLC is in a slot other than zero (like can be done with ControLogix), then you can specify the slot with the following:

```
comm.ProcessorSlot = 2
```

NOTE: If you are working with a Micro8xx PLC, you must set the Micro800 flag since the path is different:

```
comm.Micro800 = True
```

Optionally set a specific maximum size for requests/replies.  If not specified, defaults to try a Large, then a Small Forward Open (for Implicit, "Connected" sessions).

```
comm.ConnectionSize = 508
```


### Other Features

Pylogix has features other than simply reading/writing.  See the [documentation](docs/Documentation.md) for more info, see the examples directory
simple use cases for the various methods.

## FAQ

Here's a list of frequent asked questions. [faq](docs/FAQ.md)

## Authors
* **Burt Peterson** - *Initial work*
* **Dustin Roeder** - *Maintainer* - [dmroeder](https://github.com/dmroeder)
* **Fernando B. (TheFern2)** - *Contributor* - [TheFern2](https://github.com/TheFern2)
* **Ottowayi** - *Contributor* - [ottowayi](https://github.com/ottowayi)
* **Perry Kundert** - *Contributor* - [pjkundert](https://github.com/pjkundert)

## License

This project is licensed under Apache 2.0 License - see the [LICENSE](LICENSE.txt) file for details.

## Acknowledgements

* Archie of AdvancedHMI for all kinds pointers and suggestions.
* Thanks to ottowayi for general python and good practice advice
* Thanks to all of the users that have tested and provided feedback.
