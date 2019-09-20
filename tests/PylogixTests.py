from pylogix import PLC
import time
import unittest
from Randomizer import Randomizer

comm = PLC()
r = Randomizer()


class PylogixTests(unittest.TestCase):
    def compare_bool(self, tag):
        # write false
        comm.Write(tag, 0)
        response = comm.Read(tag)
        self.assertEqual(response.Value, False, response.Status)
        # write true
        comm.Write(tag, 1)
        response = comm.Read(tag)
        self.assertEqual(response.Value, True, response.Status)

    def compare_tag(self, tag, value):
        comm.Write(tag, value)
        response = comm.Read(tag)
        self.assertEqual(response.Value, value, response.Status)

    def basic_fixture(self, prefix=''):
        self.compare_bool(prefix + 'BaseBool')
        self.compare_bool(prefix + 'BaseBits.0')
        self.compare_bool(prefix + 'BaseBits.31')
        self.compare_tag(prefix + 'BaseSINT', r.Sint())
        self.compare_tag(prefix + 'BaseINT', r.Int())
        self.compare_tag(prefix + 'BaseDINT', r.Dint())
        self.compare_tag(prefix + 'BaseLINT', r.Dint())
        self.compare_tag(prefix + 'BaseReal', r.Sint())
        self.compare_tag(prefix + 'BaseSTRING', r.String())
        self.compare_tag(prefix + 'BaseTimer.PRE', abs(r.Int()))

    def basic_array_fixture(self, prefix=''):
        self.compare_bool(prefix + 'BaseBoolArray[0]')
        self.compare_bool(prefix + 'BaseBoolArray[31]')
        self.compare_bool(prefix + 'BaseBITSArray[0].0')
        self.compare_bool(prefix + 'BaseBITSArray[0].31')
        self.compare_bool(prefix + 'BaseBITSArray[31].0')
        self.compare_bool(prefix + 'BaseBITSArray[31].31')
        self.compare_tag(prefix + 'BaseSINTArray[0]', r.Sint())
        self.compare_tag(prefix + 'BaseSINTArray[31]', r.Sint())
        self.compare_tag(prefix + 'BaseINTArray[0]', r.Int())
        self.compare_tag(prefix + 'BaseINTArray[31]', r.Int())
        self.compare_tag(prefix + 'BaseDINTArray[0]', r.Dint())
        self.compare_tag(prefix + 'BaseDINTArray[31]', r.Dint())
        self.compare_tag(prefix + 'BaseLINTArray[0]', r.Dint())
        self.compare_tag(prefix + 'BaseLINTArray[31]', r.Dint())
        self.compare_tag(prefix + 'BaseREALArray[0]', r.Sint())
        self.compare_tag(prefix + 'BaseREALArray[31]', r.Sint())
        self.compare_tag(prefix + 'BaseSTRINGArray[0]', r.String())
        self.compare_tag(prefix + 'BaseSTRINGArray[31]', r.String())
        self.compare_tag(prefix + 'BaseTimerArray[0].PRE', abs(r.Int()))
        self.compare_tag(prefix + 'BaseTimerArray[31].PRE', abs(r.Int()))

    def basic_udt_fixture(self, prefix=''):
        self.compare_bool(prefix + 'UDTBasic.b_BOOL')
        self.compare_bool(prefix + 'UDTBasic.b_BITS.0')
        self.compare_bool(prefix + 'UDTBasic.b_BITS.31')
        self.compare_tag(prefix + 'UDTBasic.b_SINT', r.Sint())
        self.compare_tag(prefix + 'UDTBasic.b_INT', r.Int())
        self.compare_tag(prefix + 'UDTBasic.b_DINT', r.Dint())
        self.compare_tag(prefix + 'UDTBasic.b_LINT', r.Dint())
        self.compare_tag(prefix + 'UDTBasic.b_REAL', r.Sint())
        self.compare_tag(prefix + 'UDTBasic.b_STRING', r.String())
        self.compare_tag('UDTBasic.b_Timer.PRE', abs(r.Int()))

    def udt_array_fixture_01(self, prefix=''):
        self.compare_bool(prefix + 'UDTArray.b_BOOL[0]')
        self.compare_bool(prefix + 'UDTArray.b_BOOL[31]')
        self.compare_bool(prefix + 'UDTArray.b_BITS[0].0')
        self.compare_bool(prefix + 'UDTArray.b_BITS[0].31')
        self.compare_bool(prefix + 'UDTArray.b_BITS[31].0')
        self.compare_bool(prefix + 'UDTArray.b_BITS[31].31')
        self.compare_tag(prefix + 'UDTArray.b_SINT[0]', r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_SINT[31]', r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_INT[0]', r.Int())
        self.compare_tag(prefix + 'UDTArray.b_INT[31]', r.Int())
        self.compare_tag(prefix + 'UDTArray.b_DINT[0]', r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_DINT[31]', r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_LINT[0]', r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_LINT[31]', r.Dint())
        self.compare_tag(prefix + 'UDTArray.b_REAL[0]', r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_REAL[31]', r.Sint())
        self.compare_tag(prefix + 'UDTArray.b_STRING[0]', r.String())
        self.compare_tag(prefix + 'UDTArray.b_STRING[31]', r.String())
        self.compare_tag(prefix + 'UDTArray.b_Timer[0].PRE', abs(r.Int()))
        self.compare_tag(prefix + 'UDTArray.b_Timer[31].PRE', abs(r.Int()))

    def udt_array_fixture_02(self, prefix=''):
        self.compare_bool(prefix + 'UDTArray2[0].b_BOOL[0]')
        self.compare_bool(prefix + 'UDTArray2[0].b_BOOL[31]')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[0].0')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[0].31')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[31].0')
        self.compare_bool(prefix + 'UDTArray2[0].b_BITS[31].31')
        self.compare_tag(prefix + 'UDTArray2[0].b_SINT[0]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_SINT[31]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_INT[0]', r.Int())
        self.compare_tag(prefix + 'UDTArray2[0].b_INT[31]', r.Int())
        self.compare_tag(prefix + 'UDTArray2[0].b_DINT[0]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_DINT[31]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_LINT[0]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_LINT[31]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[0].b_REAL[0]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_REAL[31]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[0].b_STRING[0]', r.String())
        self.compare_tag(prefix + 'UDTArray2[0].b_STRING[31]', r.String())
        self.compare_tag(prefix + 'UDTArray2[0].b_Timer[0].PRE', abs(r.Int()))
        self.compare_tag(prefix + 'UDTArray2[0].b_Timer[31].PRE', abs(r.Int()))
        self.compare_bool(prefix + 'UDTArray2[31].b_BOOL[0]')
        self.compare_bool(prefix + 'UDTArray2[31].b_BOOL[31]')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[0].0')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[0].31')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[31].0')
        self.compare_bool(prefix + 'UDTArray2[31].b_BITS[31].31')
        self.compare_tag(prefix + 'UDTArray2[31].b_SINT[0]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_SINT[31]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_INT[0]', r.Int())
        self.compare_tag(prefix + 'UDTArray2[31].b_INT[31]', r.Int())
        self.compare_tag(prefix + 'UDTArray2[31].b_DINT[0]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_DINT[31]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_LINT[0]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_LINT[31]', r.Dint())
        self.compare_tag(prefix + 'UDTArray2[31].b_REAL[0]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_REAL[31]', r.Sint())
        self.compare_tag(prefix + 'UDTArray2[31].b_STRING[0]', r.String())
        self.compare_tag(prefix + 'UDTArray2[31].b_STRING[31]', r.String())
        self.compare_tag(prefix + 'UDTArray2[31].b_Timer[0].PRE', abs(r.Int()))
        self.compare_tag(
            prefix + 'UDTArray2[31].b_Timer[31].PRE', abs(r.Int()))

    def setUp(self):
        comm.IPAddress = '192.168.0.26'
        comm.ProcessorSlot = 1

    def test_basic(self):
        self.basic_fixture()
        self.basic_array_fixture()

    def test_udt(self):
        self.basic_udt_fixture()
        self.udt_array_fixture_01()
        self.udt_array_fixture_02()

    def tearDown(self):
        comm.Close()


if __name__ == "__main__":
    unittest.main()
