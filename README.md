# pylogix

This project will allow you to easily read/write values from tags in Rockwell Automation Logix based PLC's over Ethernet I/P using Python.  PLC models inclued CompactLogix, ControlLogix and Micro8xx.  Python2 and Python3 are both supported.

### NB! This project does not support PLC5, SLC or the Micrologix controllers.
### NB! The following functions GetDeviceProperties, Discover, will query device information for other vendors, as they are part of the vendors list [lgx_device.py](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_device.py). Other than that pylogix can't retrieve any other information or communicate with those devices. Please look for libraries for your PLC brand.

## Getting Started

There are currently no dependencies so you can get going quickly without having to install any other prerequiste packages.

### Installing

Install pylogix with pip (Latest version):

```
pip install pylogix
```

To install previous version before major changes (0.3.7):

```
pip install pylogix==0.3.7
```

To upgrade to the latest version:

```
pip install pylogix --upgrade
```

Alternatively, you can clone the repo and manually install it:

```
git clone https://github.com/dmroeder/pylogix.git
cd pylogix
python setup.py install --user
```

### Verifying Installation

To verify the installation on Linux, open the terminal and use the following commands:

```
python
import pylogix
pylogix.__version__
```

### Your First Script:

The cloned repository will come with many examples, I'll give one here.  We'll read one simple tag and print out the value.  All methods will return the Response class, which contains TagName, Value and Status.

```
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

Pylogix has features other than simply reading/writing.  You can see all of them in the examples, I'll also list them here

* Discover()
* GetPLCTime()
* SetPLCTime()
* GetTagList()
* GetModuleProperties(slot=0)

## Authors
* **Burt Peterson** - *Initial work*
* **Dustin Roeder** - *Maintainer* - [dmroeder](https://github.com/dmroeder)
* **Fernando B. (Kodaman2)** - *Contributor* - [TheFern2](https://github.com/TheFern2)
* **Ottowayi** - *Contributor* - [ottowayi](https://github.com/ottowayi)
* **Perry Kundert** - *Contributor* - [pjkundert](https://github.com/pjkundert)

## License

This project is licensed under Apache 2.0 License - see the [LICENSE](LICENSE.txt) file for details.

## Acknowledgements

* Archie of AdvancedHMI for all kinds pointers and suggestions.
* Thanks to ottowayi for general python and good practice advice
* Thanks to all of the users that have tested and provided feedback.
