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
