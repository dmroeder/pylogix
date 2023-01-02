"""
Build script to write vendor names bin for micropython environments
- File vendor.bin is read by app module [u]pylogix/lgx_uvendors.[m]py

Usage
=====

    python build_vendor_bin.py

This script is not part of the library.  It only needs to be run when
the vendors dict change in script pylogix/lgx_uvendors.py,, but is
called by build_mpy.sh when the upylogix/*.mpy files are rebuilt

Background
==========

Memory is typically limited in [micropython] environments, and the
vendors dict in pylogix/lgx_vendors.py uses a large chunk of RAM, such
that the pylogix library takes too much memory on some hardware devices
to be useful.

This current solution writes the vendors data to a file* with sorted,
fixed-length records, upylogix/vendor.bin, which data file can be read
by the code in pylogix/lgx_uvendors.[m]py to emulate the vendors dict.

* The assumption is that the hardware device has separate file-based
  memory, which memory does affect the available RAM space

"""

# This should never be loaded as a module
assert "__main__" == __name__,"Don't use [' + __file__ + '] as a module"

# Load vendors dict, and create sorted list of keys; set max name length
from pylogix.lgx_vendors import vendors as vdict
ks = sorted(vdict.keys())
maxL = 0

# Convert vendors to "key:vendor" byte-strings in key-sorted list
# - Also store length of longest encoded byte-string in maxL
vlist = list()
for k in ks:
    assert isinstance(k,int)
    v = vdict[k]
    assert isinstance(v,str)
    vencoded = "{0}:{1}".format(k,v).encode('UTF-8')
    vlist.append(vencoded)
    L = len(vencoded)
    if L > maxL: maxL = L

# Lambda pads byte-string to fixed length with spaces and a newline
oneline = lambda v: (v + (b' '*maxL))[:maxL] + b'\n'

# Write fixed-length records to vendors.bin file for fast lookups
with open('upylogix/vendors.bin','wb') as fbin:

    # Write an initial header record containing the vendor count
    headerstring = "{0}:{1}".format(len(ks),"Count of vendors")
    fbin.write(oneline(headerstring.encode('UTF-8')))

    # Write vendor data records
    for key_vendor in vlist: fbin.write(oneline(key_vendor))
