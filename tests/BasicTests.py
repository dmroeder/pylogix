from pylogix import PLC
import time
import unittest
from Randomizer import Randomizer

comm = PLC()
r = Randomizer()


class BasicTests(unittest.TestCase):
    def compare_bool(self, tag, prefix=''):
        # write false
        comm.Write(prefix + tag, 0)
        response = comm.Read(prefix + tag)
        self.assertEqual(response.Value, False, response.Status)
        # write true
        comm.Write(prefix + tag, 1)
        response = comm.Read(prefix + tag)
        self.assertEqual(response.Value, True, response.Status)

    def compare_tag(self, tag, value, prefix=''):
        comm.Write(prefix + tag, value)
        response = comm.Read(prefix + tag)
        self.assertEqual(response.Value, value, response.Status)

    def setUp(self):
        comm.IPAddress = '192.168.0.26'
        comm.ProcessorSlot = 1

    def test_base_bool(self):
        self.compare_bool('BaseBool')

    def test_base_bits(self):
        self.compare_bool('BaseBits.0')
        self.compare_bool('BaseBits.31')

    def test_base_ints_reals(self):
        self.compare_tag('BaseSINT', r.Sint())
        self.compare_tag('BaseINT', r.Int())
        self.compare_tag('BaseDINT', r.Dint())
        self.compare_tag('BaseLINT', r.Dint())
        self.compare_tag('BaseReal', r.Sint())

    def tearDown(self):
        comm.Close()


if __name__ == "__main__":
    unittest.main()
