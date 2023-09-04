########################################################################
# scripts/build_mpy.py
# - Cross-compile .py=>.mpy files for micropython
# - Build upylogix/lgx_uvendors.mpy.bin file from pylogix/lgx_vendors.py
# - Generate package.json
########################################################################

# This should never be loaded as a module
assert "__main__" == __name__,"Don't use [' + __file__ + '] as a module"

import os
from mpy_cross import run

# CHDIR to root of repository
script_dir = os.path.dirname(__file__)
toproot_dir = os.path.join(script_dir,'..')
os.chdir(toproot_dir)

# Compile pylogix/*.py (except lgx_vendors.py) to upylogix/*.mpy
for modyule in '__init__ eip lgx_comm lgx_device lgx_response lgx_tag utils lgx_uvendors'.split():
  argv = list()
  argv.append(os.path.join('pylogix','{0}.py'.format(modyule)))
  argv.append('-o')
  argv.append(os.path.join('upylogix','{0}.mpy'.format(modyule)))
  run(*argv)

########################################################################
build_vendors_bin_doc = """
Build script to write vendor names bin for micropython environments
- File vendors.bin is read by app module [u]pylogix/lgx_uvendors.[m]py

Usage
=====

    python build_vendors_bin.py

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
fixed-length records, upylogix/vendors.bin, which data file can be read
by the code in pylogix/lgx_uvendors.[m]py to emulate the vendors dict.

* The assumption is that the hardware device has separate file-based
  memory, which memory does affect the available RAM space

"""

# Load vendors dict, and create sorted list of keys; set max name length
import sys
sys.path.insert(0,'.')
from pylogix.lgx_vendors import vendors as vdict
ks = sorted(vdict.keys())
maxL = 0

# Convert vendors to "key:vendor" byte-strings in key-sorted list
# - Also store length of longest encoded byte-string in maxL
vlist = list()
for k in ks:
    assert isinstance(k,int)
    assert k > -1
    v = vdict[k]
    assert isinstance(v,str)
    vencoded = "{0}:{1}".format(k,v).encode('UTF-8')
    vlist.append(vencoded)
    L = len(vencoded)
    if L > maxL: maxL = L

# Lambda pads byte-string to fixed length with spaces and a newline
oneline = lambda v: (v + (b' '*maxL))[:maxL] + b'\n'

# Write fixed-length records to vendors.bin file for fast lookups
with open('upylogix/lgx_uvendors.mpy.bin','wb') as fbin:

    # Write an initial header record containing the vendor count
    headerstring = "{0}:{1}".format(len(ks),"Count of vendors")
    fbin.write(oneline(headerstring.encode('UTF-8')))

    # Write vendor data records
    for key_vendor in vlist: fbin.write(oneline(key_vendor))

########################################################################
# Generate package.json
import os
import glob
import json

from pylogix import __version__

directory_path = f'{toproot_dir}/pylogix/'
py_files_fullpath = glob.glob(os.path.join(directory_path, '*.py'))
py_files = []
# exclude lgx_vendors.py
for py_file in py_files_fullpath:
    if "lgx_vendors.py" not in py_file:
        py_files.append(os.path.basename(py_file))

# manually add lgx_uvendors.mpy.bin
py_files.append("lgx_uvendors.mpy.bin")
package_json_dict = {}
list_of_package_urls = []
for py_file in py_files:
    repo_url = "github:dmroeder/pylogix/upylogix"
    py_file = py_file.replace(".py", ".mpy")
    list_to_add = [f"pylogix/{py_file}", f"{repo_url}/{py_file}"]
    list_of_package_urls.append(list_to_add)

package_json_dict["urls"] = list_of_package_urls
package_json_dict["version"] = __version__
with open("package.json", "w") as fp:
    json.dump(package_json_dict, fp, indent=4)
