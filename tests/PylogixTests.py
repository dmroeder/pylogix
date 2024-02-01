"""
   Originally created by Burt Peterson
   Updated and maintained by Dustin Roeder (dmroeder@gmail.com)

   Copyright 2019 Dustin Roeder

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import plcConfig  # Info: tests\README.md - Setup test configuration file
import pylogix
import time
import unittest

from pylogix.lgx_response import Response
from pylogix.lgx_tag import Tag  # Need Classes for type checking
from Randomizer import Randomizer
from pylogix.utils import is_micropython, is_python2


class PylogixTests(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.comm = pylogix.PLC()
        self.r = Randomizer()

    def compare_bool(self, tag):
        # write false
        self.comm.Write(tag, 0)
        response = self.comm.Read(tag)
        self.assertEqual(response.Value, False, response.Status)
        # write true
        self.comm.Write(tag, 1)
        response = self.comm.Read(tag)
        self.assertEqual(response.Value, True, response.Status)

    def compare_tag(self, tag, value):
        self.comm.Write(tag, value)
        response = self.comm.Read(tag)
        self.assertEqual(response.Value, value, response.Status)

    def array_result(self, tagname, arraylen):
        response = self.comm.Read(tagname, arraylen)
        self.assertGreaterEqual(len(response.Value), arraylen, response.Status)

    def basic_fixture(self, prefix=''):
        self.compare_bool(prefix + 'BaseBool')
        self.compare_bool(prefix + 'BaseBits.0')
        self.compare_bool(prefix + 'BaseBits.31')
        self.compare_tag(prefix + 'BaseSINT', self.r.Sint())
        self.compare_tag(prefix + 'BaseINT', self.r.Int())
        self.compare_tag(prefix + 'BaseDINT', self.r.Dint())
        self.compare_tag(prefix + 'BaseLINT', self.r.Dint())
        self.compare_tag(prefix + 'BaseReal', self.r.Sint())
        self.compare_tag(prefix + 'BaseSTRING', self.r.String())
        self.compare_tag(prefix + 'BaseTimer.PRE', abs(self.r.Int()))

    def basic_array_fixture(self, prefix=''):
        self.compare_bool(prefix + 'BaseBoolArray[0]')
        self.compare_bool(prefix + 'BaseBoolArray[31]')
        self.compare_bool(prefix + 'BaseBITSArray[0].0')
        self.compare_bool(prefix + 'BaseBITSArray[0].31')
        self.compare_bool(prefix + 'BaseBITSArray[31].0')
        self.compare_bool(prefix + 'BaseBITSArray[31].31')
        self.compare_tag(prefix + 'BaseSINTArray[0]', self.r.Sint())
        self.compare_tag(prefix + 'BaseSINTArray[31]', self.r.Sint())
        self.compare_tag(prefix + 'BaseINTArray[0]', self.r.Int())
        self.compare_tag(prefix + 'BaseINTArray[31]', self.r.Int())
        self.compare_tag(prefix + 'BaseDINTArray[0]', self.r.Dint())
        self.compare_tag(prefix + 'BaseDINTArray[31]', self.r.Dint())
        self.compare_tag(prefix + 'BaseLINTArray[0]', self.r.Dint())
        self.compare_tag(prefix + 'BaseLINTArray[31]', self.r.Dint())
        self.compare_tag(prefix + 'BaseREALArray[0]', self.r.Sint())
        self.compare_tag(prefix + 'BaseREALArray[31]', self.r.Sint())
        self.compare_tag(prefix + 'BaseSTRINGArray[0]', self.r.String())
        self.compare_tag(prefix + 'BaseSTRINGArray[31]', self.r.String())
        self.compare_tag(prefix + 'BaseTimerArray[0].PRE', abs(self.r.Int()))
        self.compare_tag(prefix + 'BaseTimerArray[31].PRE', abs(self.r.Int()))
        self.compare_tag(prefix + 'MultiDim[1,1,1]', self.r.Dint())
        self.compare_tag(prefix + 'MultiString[1,1,1].LEN', self.r.Sint())

    def udt_basic_fixture(self, prefix=''):
        self.compare_bool(prefix + 'UDTBasic.b_BOOL')
        self.compare_bool(prefix + 'UDTBasic.b_BITS.0')
        self.compare_bool(prefix + 'UDTBasic.b_BITS.31')
        self.compare_tag(prefix + 'UDTBasic.b_SINT', self.r.Sint())
        self.compare_tag(prefix + 'UDTBasic.b_INT', self.r.Int())
        self.compare_tag(prefix + 'UDTBasic.b_DINT', self.r.Dint())
        self.compare_tag(prefix + 'UDTBasic.b_LINT', self.r.Dint())
        self.compare_tag(prefix + 'UDTBasic.b_REAL', self.r.Sint())
        self.compare_tag(prefix + 'UDTBasic.b_STRING', self.r.String())
        self.compare_tag('UDTBasic.b_Timer.PRE', abs(self.r.Int()))

    def udt_array_fixture_01(self, prefix=''):
        self.compare_bool(prefix + 'UDTArray.b_BOOL[0]')
        self.compare_bool(prefix + 'UDTArray.b_BOOL[31]')
        self.compare_bool(prefix + 'UDTArray.b_BITS[0].0')
        self.compare_bool(prefix + 'UDTArray.b_BITS[0].31')
        self.compare_bool(prefix + 'UDTArray.b_BITS[31].0')
        self.compare_bool(prefix + 'UDTArray.b_BITS[31].31')
        self.compare_tag(prefix + 'UDTArray.b_SINT[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_SINT[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_INT[0]', self.r.Int())
        self.compare_tag(prefix + 'UDTArray.b_INT[31]', self.r.Int())
        self.compare_tag(prefix + 'UDTArray.b_DINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_DINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_LINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_LINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_REAL[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_REAL[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_STRING[0]', self.r.String())
        self.compare_tag(prefix + 'UDTArray.b_STRING[31]', self.r.String())
        self.compare_tag(prefix + 'UDTArray.b_Timer[0].PRE', abs(self.r.Int()))
        self.compare_tag(prefix + 'UDTArray.b_Timer[31].PRE', abs(self.r.Int()))

    def udt_array_fixture_02(self, prefix=''):
        self.compare_bool(prefix + 'UDTArray2[0].b_BOOL[0]')
        self.compare_bool(prefix + 'UDTArray2[0].b_BOOL[31]')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[0].0')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[0].31')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[31].0')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[31].31')
        self.compare_tag(prefix + 'UDTArray2[0].b_SINT[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_SINT[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_INT[0]', self.r.Int())
        self.compare_tag(prefix + 'UDTArray2[0].b_INT[31]', self.r.Int())
        self.compare_tag(prefix + 'UDTArray2[0].b_DINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_DINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_LINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_LINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_REAL[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_REAL[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_STRING[0]', self.r.String())
        self.compare_tag(prefix + 'UDTArray2[0].b_STRING[31]', self.r.String())
        self.compare_tag(prefix + 'UDTArray2[0].b_Timer[0].PRE', abs(self.r.Int()))
        self.compare_tag(prefix + 'UDTArray2[0].b_Timer[31].PRE', abs(self.r.Int()))
        self.compare_bool(prefix + 'UDTArray2[31].b_BOOL[0]')
        self.compare_bool(prefix + 'UDTArray2[31].b_BOOL[31]')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[0].0')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[0].31')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[31].0')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[31].31')
        self.compare_tag(prefix + 'UDTArray2[31].b_SINT[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_SINT[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_INT[0]', self.r.Int())
        self.compare_tag(prefix + 'UDTArray2[31].b_INT[31]', self.r.Int())
        self.compare_tag(prefix + 'UDTArray2[31].b_DINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_DINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_LINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_LINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_REAL[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_REAL[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_STRING[0]', self.r.String())
        self.compare_tag(prefix + 'UDTArray2[31].b_STRING[31]', self.r.String())
        self.compare_tag(prefix + 'UDTArray2[31].b_Timer[0].PRE', abs(self.r.Int()))
        self.compare_tag(
            prefix + 'UDTArray2[31].b_Timer[31].PRE', abs(self.r.Int()))

    def udt_combined_fixture(self, prefix=''):
        self.compare_bool(prefix + 'UDTCombined.c_Array.b_BOOL[0]')
        self.compare_bool(prefix + 'UDTCombined.c_Array.b_BOOL[31]')
        self.compare_bool(prefix + 'UDTCombined.c_Array.b_BITS[0].0')
        self.compare_bool(prefix + 'UDTCombined.c_Array.b_BITS[0].31')
        self.compare_bool(prefix + 'UDTCombined.c_Array.b_BITS[31].0')
        self.compare_bool(prefix + 'UDTCombined.c_Array.b_BITS[31].31')
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_SINT[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_SINT[31]', self.r.Sint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_INT[0]', self.r.Int())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_INT[31]', self.r.Int())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_DINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_DINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_LINT[0]', self.r.Dint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_LINT[31]', self.r.Dint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_REAL[0]', self.r.Sint())
        self.compare_tag(prefix + 'UDTCombined.c_Array.b_REAL[31]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombined.c_Array.b_STRING[0]', self.r.String())
        self.compare_tag(
            prefix + 'UDTCombined.c_Array.b_STRING[31]', self.r.String())
        self.compare_tag(
            prefix + 'UDTCombined.c_Array.b_Timer[0].PRE', abs(self.r.Int()))
        self.compare_tag(
            prefix + 'UDTCombined.c_Array.b_Timer[31].PRE', abs(self.r.Int()))

    def udt_combined_array_fixture(self, prefix=''):
        self.compare_bool(prefix + 'UDTCombinedArray[0].c_Array.b_BOOL[0]')
        self.compare_bool(prefix + 'UDTCombinedArray[0].c_Array.b_BOOL[31]')
        self.compare_bool(prefix + 'UDTCombinedArray[0].c_Array.b_BITS[0].0')
        self.compare_bool(prefix + 'UDTCombinedArray[0].c_Array.b_BITS[0].31')
        self.compare_bool(prefix + 'UDTCombinedArray[0].c_Array.b_BITS[31].0')
        self.compare_bool(prefix + 'UDTCombinedArray[0].c_Array.b_BITS[31].31')
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_SINT[0]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_SINT[31]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_INT[0]', self.r.Int())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_INT[31]', self.r.Int())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_DINT[0]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_DINT[31]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_LINT[0]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_LINT[31]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_REAL[0]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_REAL[31]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_STRING[0]', self.r.String())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_STRING[31]', self.r.String())
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_Timer[0].PRE',
            abs(self.r.Int()))
        self.compare_tag(
            prefix + 'UDTCombinedArray[0].c_Array.b_Timer[31].PRE',
            abs(self.r.Int()))
        self.compare_bool(prefix + 'UDTCombinedArray[9].c_Array.b_BOOL[0]')
        self.compare_bool(prefix + 'UDTCombinedArray[9].c_Array.b_BOOL[31]')
        self.compare_bool(prefix + 'UDTCombinedArray[9].c_Array.b_BITS[0].0')
        self.compare_bool(prefix + 'UDTCombinedArray[9].c_Array.b_BITS[0].31')
        self.compare_bool(prefix + 'UDTCombinedArray[9].c_Array.b_BITS[31].0')
        self.compare_bool(prefix + 'UDTCombinedArray[9].c_Array.b_BITS[31].31')
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_SINT[0]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_SINT[31]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_INT[0]', self.r.Int())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_INT[31]', self.r.Int())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_DINT[0]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_DINT[31]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_LINT[0]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_LINT[31]', self.r.Dint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_REAL[0]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_REAL[31]', self.r.Sint())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_STRING[0]', self.r.String())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_STRING[31]', self.r.String())
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_Timer[0].PRE',
            abs(self.r.Int()))
        self.compare_tag(
            prefix + 'UDTCombinedArray[9].c_Array.b_Timer[31].PRE',
            abs(self.r.Int()))

    def read_array_fixture(self, prefix=''):
        self.array_result('BaseBOOLArray[0]', 10)
        self.array_result('BaseSINTArray[0]', 10)
        self.array_result('BaseINTArray[0]', 10)
        self.array_result('BaseDINTArray[0]', 10)
        self.array_result('BaseLINTArray[0]', 10)
        self.array_result('BaseREALArray[0]', 10)
        self.array_result('BaseSTRINGArray[0]', 10)
        self.array_result('BaseBOOLArray[10]', 10)
        self.array_result('BaseSINTArray[10]', 10)
        self.array_result('BaseINTArray[10]', 10)
        self.array_result('BaseDINTArray[10]', 10)
        self.array_result('BaseLINTArray[10]', 10)
        self.array_result('BaseREALArray[10]', 10)
        self.array_result('BaseSTRINGArray[10]', 10)

    def multi_read_fixture(self, tags):
        response = self.comm.Read(tags)
        self.assertEqual(len(response), len(
            tags), 'Unable to read multiple tags!')

        for i in range(len(response)):
            self.assertEqual('Success', response[i].Status)

    def bool_list_fixture(self, length=8):
        bool_list = []
        for i in range(length):
            bool_list.append('BaseBOOLArray[{}]'.format(i))
        return bool_list

    def nemesis_fixture(self, tag, length):
        # test write BOOL array
        true_val = [1 for i in range(length)]
        false_val = [0 for i in range(length)]

        # write array to 0
        self.comm.Write(tag, false_val)
        ret = self.comm.Read(tag, length).Value
        self.assertEqual(ret, false_val, "Failed to write nemesis to 0")

        # write array to 1
        self.comm.Write(tag, true_val)
        ret = self.comm.Read(tag, length).Value
        self.assertEqual(ret, true_val, "Failed to write nemesis to 1")

    def large_list_fixture(self):
            length = 50
            tags = ["Str{}".format(i) for i in range(length)]
            vals = [self.r.String() for i in range(length)]

            req = [[tags[i], vals[i]] for i in range(length)]
            self.comm.Write(req)

            ret = self.comm.Read(tags)
            read_vals = [r.Value for r in ret]

            self.assertEqual(vals, read_vals, "Failed to write large list")

    def test_with_datatype(self):
        """
        Try a few variations of reads when including data type
        """
        self.comm.KnownTags = {}
        value = self.r.Dint()
        self.comm.Write("BaseDINT", value, 0xc4)
        self.comm.KnownTags = {}
        ret = self.comm.Read("BaseDINT", 1, 0xc4).Value
        self.assertEqual(value, ret, "Failed when including data type")

        # try with a list/tuple, but only one instance
        value = self.r.Int()
        self.comm.KnownTags = {}
        write_request = [("BaseINT", value, 0xc3)]
        self.comm.Write(write_request)
        
        read_request = [("BaseINT", 1, 0xc3)] 
        self.comm.KnownTags = {}
        ret = self.comm.Read(read_request)

        self.assertEqual(value, ret[0].Value, "Failed read list of one with data type")

        # try a list with multiple values and data type
        values = [self.r.Sint() for i in range(10)]
        write_request = [("BaseSINTArray[{}]".format(i), values[i], 0xc2) for i in range(10)]
        read_request = [("BaseSINTArray[{}]".format(i), 1, 0xc2) for i in range(10)]
        self.KnownTags = {}
        self.comm.Write(write_request)
        
        self.KnownTags = {}
        ret = self.comm.Read(read_request)
        return_values = [r.Value for r in ret]

        self.assertEqual(values, return_values, "Failed reading a list with data type")

    def write_array_fixture(self):
        
        # clear the values before trying to write
        for i in range(6):
            self.comm.Write("BaseSINTArray[{}]".format(i), 0)
            self.comm.Write("BaseINTArray[{}]".format(i), 0)
            self.comm.Write("BaseDINTArray[{}]".format(i), 0)
            self.comm.Write("BaseLINTArray[{}]".format(i), 0)
            self.comm.Write("BaseREALArray[{}]".format(i), 0)
            self.comm.Write("BaseSTRINGArray[{}]".format(i), "")

        values = [i for i in range(100)]
        self.comm.Write("BaseSINTArray[0]", values)
        return_values = self.comm.Read("BaseSINTArray[0]", len(values)).Value
        self.assertEqual(values, return_values, "Failed to write array of SINT values")

        values = [i for i in range(100)]
        self.comm.Write("BaseINTArray[0]", values)
        return_values = self.comm.Read("BaseINTArray[0]", len(values)).Value
        self.assertEqual(values, return_values, "Failed to write array of INT values")

        values = [i for i in range(100)]
        self.comm.Write("BaseDINTArray[0]", values)
        return_values = self.comm.Read("BaseDINTArray[0]", len(values)).Value
        self.assertEqual(values, return_values, "Failed to write array of DINT values")

        values = [i for i in range(100)]
        self.comm.Write("BaseLINTArray[0]", values)
        return_values = self.comm.Read("BaseLINTArray[0]", len(values)).Value
        self.assertEqual(values, return_values, "Failed to write array of LINT values")

        values = [i for i in range(100)]
        self.comm.Write("BaseREALArray[0]", values)
        return_values = self.comm.Read("BaseREALArray[0]", len(values)).Value
        self.assertEqual(values, return_values, "Failed to write array of REAL values")

        values = ["String{}".format(i) for i in range(100)]
        self.comm.Write("BaseSTRINGArray[0]", values)
        return_values = self.comm.Read("BaseSTRINGArray[0]", len(values)).Value
        self.assertEqual(values, return_values, "Failed to write array of STRING values")


    def setUp(self):
        self.comm.IPAddress = plcConfig.plc_ip
        self.comm.ProcessorSlot = plcConfig.plc_slot
        self.comm.Micro800 = plcConfig.isMicro800

    @unittest.skipIf(plcConfig.isMicro800,'for Micro800')
    def test_basic(self):
        self.basic_fixture()
        self.basic_array_fixture()
        self.basic_fixture('PROGRAM:MainProgram.p')
        self.basic_array_fixture('PROGRAM:MainProgram.p')

    @unittest.skipIf(plcConfig.isMicro800,'for Micro800')
    def test_udt(self):
        self.udt_basic_fixture()
        self.udt_array_fixture_01()
        self.udt_array_fixture_02()
        self.udt_basic_fixture('PROGRAM:MainProgram.p')
        self.udt_array_fixture_01('PROGRAM:MainProgram.p')
        self.udt_array_fixture_02('PROGRAM:MainProgram.p')

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_combined(self):
        self.udt_combined_fixture()
        self.udt_combined_array_fixture()
        self.udt_combined_fixture('PROGRAM:MainProgram.p')
        self.udt_combined_array_fixture('PROGRAM:MainProgram.p')

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_array(self):
        self.read_array_fixture()
        self.read_array_fixture('PROGRAM:MainProgram.p')

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_multi_read(self):
        tags = ['BaseDINT', 'BaseINT', 'BaseSTRING']
        self.multi_read_fixture(tags)

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_bool_list(self):
        tags = self.bool_list_fixture(128)
        self.multi_read_fixture(tags)

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_nemesis_write(self):
        self.nemesis_fixture("Nemesis[0]", 64)

    def test_array_write(self):
        self.write_array_fixture()

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_large_list(self):
        self.large_list_fixture()

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    def test_large_list(self):
        self.test_with_datatype()

    @unittest.skipIf(is_micropython(), 'No gethostname in micropython socket module')
    def test_discover(self):
        devices = self.comm.Discover()
        self.assertEqual(devices.Status, 'Success', devices.Status)

    @unittest.skipIf(plcConfig.isMicro800, 'for Micro800')
    @unittest.skipIf(is_micropython(), 'No daylight in micropython time module')
    def test_time(self):
        self.comm.SetPLCTime()
        time = self.comm.GetPLCTime()
        self.assertEqual(time.Status, 'Success', time.Status)

    def test_get_tags(self):
        tags = self.comm.GetTagList()
        self.assertEqual(tags.Status, 'Success', tags.Status)

    def test_unexistent_tags(self):
        expected_msg = (plcConfig.isMicro800
            and 'Path destination unknown'
            or 'Path segment error'
            )
        response = self.comm.Read('DumbTag')
        self.assertEqual(
            response.Status, expected_msg, response.Status)
        write_response = self.comm.Write('DumbTag', 10)
        self.assertEqual(
            write_response.Status, expected_msg, write_response.Status)

    def test_lgx_tag_class(self):
        tags = self.comm.GetTagList()
        self.assertEqual(
            isinstance(
                tags.Value[0], Tag), True, "LgxTag not found in GetTagList")

    def test_response_class(self):
        one_bool = self.comm.Read('BaseBool')
        self.assertEqual(
            isinstance(one_bool, Response),
            True, "Response class not found in Read")
        bool_tags = ['BaseBool', 'BaseBits.0', 'BaseBits.31']
        booleans = self.comm.Read(bool_tags)
        self.assertEqual(
            isinstance(booleans[0], Response),
            True, "Response class not found in Multi Read")
        bool_write = self.comm.Write('BaseBool', 1)
        self.assertEqual(
            isinstance(bool_write, Response),
            True, "Response class not found in Write")

    @unittest.skipIf(plcConfig.isMicro800,'for Micro800')
    def test_program_list(self):
        programs = self.comm.GetProgramsList()
        self.assertEqual(programs.Status, 'Success', programs.Status)
        self.assertEqual(
            isinstance(programs, Response),
            True, "Response class not found in GetProgramsList")

    @unittest.skipIf(plcConfig.isMicro800,'for Micro800')
    def test_program_tag_list(self):
        program_tags = self.comm.GetProgramTagList('Program:MainProgram')
        self.assertEqual(program_tags.Status, 'Success', program_tags.Status)
        self.assertEqual(
            isinstance(program_tags, Response),
            True, "Response class not found in GetProgramTagList")
        self.assertEqual(
            isinstance(program_tags.Value[0], Tag),
            True, "LgxTag class not found in GetProgramTagList Value")

    def test_micro_800_init(self):
        self.assertFalse(pylogix.PLC().Micro800)
        self.assertFalse(pylogix.PLC(Micro800=False).Micro800)
        self.assertTrue(pylogix.PLC(Micro800=True).Micro800)

    @unittest.skipIf(is_micropython(), 'Not loading vendors dict into micropython')
    def test_all_uvendors(self):
        from pylogix.lgx_uvendors import uvendors
        vendors = pylogix.lgx_vendors.vendors
        for k in vendors:
            self.assertEqual(uvendors[k], vendors[k], "Mismatch vendors/uvendors")

    @unittest.skipIf(not is_micropython(), 'Not testing uvendors for python')
    def test_known_uvendors(self):
        from pylogix.lgx_uvendors import uvendors
        self.assertEqual(uvendors[26], 'Festo', "Festo uvendor not found")
        self.assertEqual(uvendors[1], 'Rockwell Automation/Allen-Bradley', "Rockwell uvendor not found")
        self.assertEqual(uvendors[-1], 'Unknown', "Unknown uvendor not returned")
        self.assertEqual(uvendors[(1<<32)-1], 'Unknown', "Unknown uvendor not returned")

    def test_unknown_attribute_in_plc(self):
        with self.assertRaises(AttributeError):
            getattr(self.comm, 'undefined_attribute')

    def tearDown(self):
        self.comm.Close()


if __name__ == "__main__":
    unittest.main()
