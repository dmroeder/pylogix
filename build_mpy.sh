#!/usr/bin/env bash

# compile
mpy-cross pylogix/__init__.py -o upylogix/__init__.mpy
mpy-cross pylogix/eip.py -o upylogix/eip.mpy
mpy-cross pylogix/lgx_comm.py -o upylogix/lgx_comm.mpy
mpy-cross pylogix/lgx_device.py -o upylogix/lgx_device.mpy
mpy-cross pylogix/lgx_response.py -o upylogix/lgx_response.mpy
mpy-cross pylogix/lgx_tag.py -o upylogix/lgx_tag.mpy
mpy-cross pylogix/utils.py -o upylogix/utils.mpy
mpy-cross pylogix/lgx_uvendors.py -o upylogix/lgx_uvendors.mpy

python build_vendor_bin.py

time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is v.vendors[k]])'
#time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors.getitem_O_N(k)])'
time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors.getitem_O_logN(k)])'
time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors[k]])'
micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;assert not [None for k in v.vendors if v.vendors[k] != u.uvendors[k]];assert "Unknown" == u.uvendors[-1];assert "Unknown" == u.uvendors[1048576];print("\nSuccess")'
