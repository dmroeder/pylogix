# lgx_uvendors.py/.mpy
# Micropython proxy class for large dict vendors in lgx_vendors.py
from pylogix.utils import is_python2


class Uvendors:
    # Look up on the fly without loading all vendor data into memory
    # .__getitem__ method is called when evaluating `uvendors[id]`
    def __getitem__(self, vendorID):
        return self.getitem_O_logN(vendorID)

    def getitem_O_logN(self, vendorID):

        vc = str(vendorID).encode('UTF-8') + b':'  # vendorID: byte-str
        colonpos = vc.index(b':')  # colon position

        # Vendor data file will be installed as [lgx_uvendors.mpy.bin],
        # with fixed-length records of UTF-8-encoded byte0strings,
        # terminated by newlines
        if is_python2():
            file_name = __file__.replace("pyc", "py") + ".bin"
        else:
            file_name = __file__ + ".bin"

        # with open(__file__ + ".bin", 'rb') as vendor_file:
        with open(file_name, 'rb') as vendor_file:

            # Read entire header line (through first newline):
            # - parse record count from decimal digits before colon;
            # - get fixed record length;
            # - calculate 0-based cardinalities of first record and of
            #   record one past the last record.
            lread = vendor_file.readline()
            span = int(lread[:lread.index(b':')])
            fixedlength = len(lread)
            assert fixedlength > 12, 'Invalid vendors.bin file'
            lo, hi = 1, 1 + span

            # Read vendor ID plus colon of next (first data) record
            lread = vendor_file.read(12)

            # Check that vendor ID, return if vendorID argument matches
            if lread.startswith(vc):
                # Read balance of line, reconstruct vendor data
                return (lread[colonpos + 1:]
                        + vendor_file.read(fixedlength - 13)
                        ).rstrip().decode('UTF-8')

            elif lread[colonpos:colonpos + 1] == b':' and lread > vc:
                # Short-circuit the binary search if invariant fails
                span = 0
            elif lread.index(b':') > colonpos:
                span = 0

            # Binary search
            # - Invariant is (vendor ID of record [lo]) < vendorID
            while span > 1:

                # Read vendor ID of record ~halfway between lo and hi
                mid = lo + (span >> 1)
                vendor_file.seek(mid * fixedlength, 0)
                lread = vendor_file.read(12)

                # Check that vendor ID, return if vendorID arg matches
                if lread.startswith(vc):
                    # Read balance of line, reconstruct vendor data
                    return (lread[colonpos + 1:]
                            + vendor_file.read(fixedlength - 13)
                            ).rstrip().decode('UTF-8')

                # Maintain invariant by assigning mid to either lo or hi
                if lread[colonpos:colonpos + 1] == b':' and lread < vc:
                    lo = mid
                elif lread.index(b':') < colonpos:
                    lo = mid
                else:
                    hi = mid

                # Re-calculate magnitude of remaining hi:lo range
                span = hi - lo

            # No match found, return vendor data indicating same
            return 'Unknown'

    # Obsolete O(N) lookup, replaced by O(logN) lookup above
    def getitem_O_N(self, vendorID):
        sID = str(vendorID)
        with open(__file__ + ".txt") as vendor_data:
            for line in vendor_data:
                # i) Split line into colon-separated tokens
                # ii) If first token does not match vendorID, continue
                # iii) Else Re-join remaining tokens and return
                tokens = line.split(':')
                if sID != tokens.pop(0): continue
                return ':'.join(tokens)
        # No tokens matched vendorID, return unknown result
        return 'Unknown'

    # Do-nothing on class initialization
    def __init__(self):
        pass

    # Test if vendorID is in file of vendor IDs
    # .__contains__ method is called when executing `id in uvendors`
    # - use .__getitem__ method above
    def __contains__(self, vendorID):
        return self[vendorID] != 'Unknown'


uvendors = Uvendors()
