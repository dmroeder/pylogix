# Micropython proxy class for large dict vendors in lgx_vendors.py
class UVENDORS:
    # Look up on the fly without loading all vendor data into memory
    # .__getitem__ method is called when evaluating `uvendors[id]`
    def __getitem__(self, vendorID):
        return self.getitem_O_logN(vendorID)

    def getitem_O_logN(self, vendorID):

        bnl,bcln = b'\n',b':'
        fc = lambda bites: bites.index(bcln)
        vID = lambda bites: bites[:fc(bites)]
        idval = lambda lyne: int(vID(lyne))

        with open(__file__ + ".bin",'rb') as vendor_file:

            # Read and validate header line (through first newline),
            # parse number of records, get fixed record length
            hdr = vendor_file.readline()
            assert bnl == hdr[-1:]
            assert b':Count of vendors' == hdr[fc(hdr):].strip()
            span = idval(hdr)
            lo,hi,fixedlength = 1, 1+span, len(hdr)

            # Read and validate first data line, i.e. next line
            lin1 = vendor_file.readline()
            assert len(lin1) == fixedlength
            assert bnl == lin1[-1:]

            # Parse vendor ID from first data line, check for match
            idval1 = idval(lin1)
            if idval1 == vendorID:
                return lin1[fc(lin1)+1:].strip().decode('UTF-8')
            elif idval1 > vendorID:
                # Short-circuit the binary search if invariant fails
                span = 0

            # Binary search; invariant is vID(line@lo) < vendorID
            while span > 1:
                mid = lo + (span >> 1)
                seek = (mid*fixedlength) - 1
                assert vendor_file.seek(seek,0) == seek
                lread = vendor_file.read(fixedlength+1)
                assert bnl == lread[:1]
                assert bnl == lread[-1:]
                iID = idval(lread[1:])
                if iID == vendorID:
                    return lread[fc(lread)+1:].strip().decode('UTF-8')
                elif iID < vendorID: lo = mid
                else               : hi = mid
                span = hi - lo
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


uvendors = UVENDORS()
