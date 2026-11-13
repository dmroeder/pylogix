"""
Offline tests for reading a UDT template (Read Template, service 0x4c).

These run without a PLC: a fake connection answers the template requests
the way a target that holds exactly words * 4 - 23 octets of definition
does. Run with: python -m unittest tests.test_read_template
"""
import os
import sys
import unittest
from struct import pack, unpack_from

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pylogix import PLC  # noqa: E402
from pylogix.lgx_tag import Tag  # noqa: E402


def _definition(name, members):
    """Template definition: 8 octets per member, then 'Name;n...' and the
    member names, NUL terminated."""
    out = b''
    for i, _ in enumerate(members):
        # array size, type DINT (0xc4), offset
        out += pack('<HHI', 0, 0xc4, i * 4)
    # name, ';n', then per member a scope pair (no NUL octets)
    out += name.encode() + b';n' + b'\x01\x03' * len(members) + b'\x00'
    for m in members:
        out += m.encode() + b'\x00'
    return out


def _words(n):
    """Attribute 4 for a definition of n octets: words * 4 - 23 >= n."""
    return (n + 23 + 3) // 4


class FakeConn(object):
    """Answers Get Attribute List and Read Template for one template.

    end_status is what the target answers to a read that starts at or
    beyond the end of the definition: 0 (an empty success) or a CIP error.
    """

    def __init__(self, definition, member_count, end_status, max_fragment=None):
        self.total = _words(len(definition)) * 4 - 23
        self.definition = definition + b'\x00' * (self.total - len(definition))
        self.member_count = member_count
        self.end_status = end_status
        self.max_fragment = max_fragment
        self.reads = []

    @staticmethod
    def _reply(service, status, data=b''):
        return b'\x00' * 46 + pack('<BBBB', service | 0x80, 0, status, 0) + data

    def connect(self, connected=True):
        return True, ''

    def send(self, request, connected=True, slot=None):
        service = unpack_from('<B', request, 0)[0]
        if service == 0x03:
            words = _words(len(self.definition))
            data = pack('<H', 4)
            data += pack('<HHI', 4, 0, words)
            data += pack('<HHH', 3, 0, 0)
            data += pack('<HHH', 2, 0, self.member_count)
            data += pack('<HHH', 1, 0, 0x1234)
            return 0, self._reply(service, 0, data)
        if service == 0x4c:
            offset, length = unpack_from('<IH', request, len(request) - 6)
            self.reads.append((offset, length))
            if len(self.reads) > 10:
                raise AssertionError('Read Template repeated: %r' % self.reads)
            if offset >= self.total:
                return self.end_status, self._reply(service, self.end_status)
            part = self.definition[offset:offset + length]
            status = 0
            if self.max_fragment and len(part) > self.max_fragment:
                part, status = part[:self.max_fragment], 0x06
            return status, self._reply(service, status, part)
        raise AssertionError('unexpected service 0x%02x' % service)


def _struct_tag(type_value):
    tag = Tag()
    tag.TagName = 'Recipe'
    tag.Struct = 1
    tag.SymbolType = 0
    tag.DataTypeValue = type_value
    return tag


class ReadTemplateTests(unittest.TestCase):

    def _read(self, end_status, max_fragment=None):
        definition = _definition('Recipe_t', ['Speed', 'Count'])
        conn = FakeConn(definition, 2, end_status, max_fragment)
        plc = PLC()
        plc.conn = conn
        tags = [_struct_tag(0x0abc)]
        plc._get_udt(tags)
        return plc, tags, conn

    def _check(self, plc, tags):
        self.assertEqual(tags[0].DataType, 'Recipe_t')
        udt = plc.UDT[0x0abc]
        self.assertEqual([f.TagName for f in udt.Fields], ['Speed', 'Count'])

    def test_end_answered_with_empty_success(self):
        """A target that answers a read at the end with an empty success
        must not make pylogix repeat the read forever."""
        plc, tags, conn = self._read(end_status=0)
        self._check(plc, tags)
        self.assertTrue(all(o < conn.total for o, _ in conn.reads), conn.reads)

    def test_end_refused(self):
        """A target that refuses a read at the end (Invalid Parameter)."""
        plc, tags, conn = self._read(end_status=0x20)
        self._check(plc, tags)
        self.assertTrue(all(o < conn.total for o, _ in conn.reads), conn.reads)

    def test_fragmented(self):
        """Partial transfer (0x06) still reads the whole definition."""
        plc, tags, conn = self._read(end_status=0x20, max_fragment=8)
        self._check(plc, tags)
        self.assertGreater(len(conn.reads), 1)


if __name__ == '__main__':
    unittest.main()
