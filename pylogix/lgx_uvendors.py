### Micropython proxy class for large dict vendors in lgx_vendors.py
class UVENDORS:
    ### Look up on the fly without loading all vendor data into memory
    ### .__getitem__ method is called when evaluating `uvendors[id]`
    def __getitem__(self,vendorID):
        sID = str(vendorID)
        with open(__file__+".txt") as vendor_data:
            for line in vendor_data:
                k, v = line.split(':')
                if k == sID: return v.strip()
        return 'Unknown'

    ### Do-nothing on class initialization
    def __init__(self): pass

    ### Test if vendorID is in file of vendor IDs
    ### .__contains__ method is called when executing `id in uvendors`
    ### - use .__getitem__ method above
    def __contains__(self,vendorID): return self[vendorID]!='Unknown'

uvendors = UVENDORS()
