from .lgxDevice import LGXDevice
from .eip import PLC, RouteAddressToSelfError, CIPConnectionError
__version_info__ = (0, 5, 1)
__version__ = '.'.join(str(x) for x in __version_info__)
