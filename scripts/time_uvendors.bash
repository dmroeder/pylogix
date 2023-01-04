#!/usr/bin/env bash

time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is v.vendors[k]])'
#time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors.getitem_O_N(k)])'
time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors.getitem_O_logN(k)])'
time micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;print([None for k in v.vendors if "Unknown" is u.uvendors[k]])'
micropython -c 'import pylogix.lgx_vendors as v;import pylogix.lgx_uvendors as u;assert not [None for k in v.vendors if v.vendors[k] != u.uvendors[k]];assert "Unknown" == u.uvendors[-1];assert "Unknown" == u.uvendors[1048576];print("\nSuccess")'
