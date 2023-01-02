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

python << EoFPython
from pylogix.lgx_vendors import vendors as vdict
vlist = list()
ks = sorted(vdict.keys())
maxL = 0

for k in ks:
    assert isinstance(k,int)
    v = vdict[k]
    assert isinstance(v,str)
    vencoded = "{0}:{1}".format(k,v).encode('UTF-8')
    vlist.append(vencoded)
    L = len(vencoded)
    if L > maxL: maxL = L

newline = b'\n'
maxspaces = b' ' * maxL

oneline = lambda v: (v + maxspaces)[:maxL] + newline

with open('upylogix/vendors.bin','wb') as fbin:
    headerstring = "{0}:{1}".format(len(ks),"Count of vendors")
    fbin.write(oneline(headerstring.encode('UTF-8')))
    for bin in vlist: fbin.write(oneline(bin))
EoFPython

time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is v.vendors[k]])'
#time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors.getitem_O_N(k)])'
time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors.getitem_O_logN(k)])'
time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors[k]])'
micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;assert not [None for k in v.vendors if v.vendors[k] != u.uvendors[k]];assert "Unknown" == u.uvendors[-1];assert "Unknown" == u.uvendors[1048576];print("\nSuccess")'
