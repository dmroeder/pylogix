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

        vc = str(vendorID).encode('UTF-8')  # vendorID as string
        cp = len(vc)                        # colon position
        vc += b':'                          # append colon

        with open(__file__ + ".bin",'rb') as vendor_file:

            # Read and validate header line (through first newline),
            # parse number of records, get fixed record length
            lread = vendor_file.readline()
            span = int(lread[:lread.index(bcln)])
            lo,hi,fixedlength = 1, 1+span, len(lread)

            # Read at least vendor ID digits plus colon from file
            lread = vendor_file.read(12)

            # Check vendor ID for match
            if lread.startswith(vc):
                return (lread[cp+1:]
                       +vendor_file.read(fixedlength-13)
                       ).rstrip().decode('UTF-8')
            elif lread[cp:cp+1] == b':' and lread > vc:
                # Short-circuit the binary search if invariant fails
                span = 0
            elif fc(lread) > cp:
                span = 0

            # Binary search; invariant is vID(line@lo) < vendorID
            while span > 1:
                mid = lo + (span >> 1)
                vendor_file.seek(mid*fixedlength,0)
                lread = vendor_file.read(12)

                if lread.startswith(vc):
                    return (lread[cp+1:]
                           +vendor_file.read(fixedlength-13)
                           ).rstrip().decode('UTF-8')

                if lread[cp:cp+1] == b':' and lread < vc: lo = mid
                elif fc(lread) < cp                     : lo = mid
                else                                    : hi = mid
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
