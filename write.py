#! /usr/bin/env /usr/bin/python
import eip as PLC
import sys


def main():
  
  PLC.__init__()			# initialize PLC object
  PLC.OpenConnection("192.168.1.10")	# connect to PLC
  
  plctag = "TestBOOL"
  PLC.WriteStuffs(plctag, 1, "BOOL")
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestSINT"
  PLC.WriteStuffs(plctag, 42, "SINT")
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestINT"
  PLC.WriteStuffs(plctag, 44, "INT")
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestDINT"
  PLC.WriteStuffs(plctag, 46, "DINT")
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestREAL"
  PLC.WriteStuffs(plctag, 11.23, "REAL")
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestSTRING"
  PLC.WriteStuffs(plctag, "SuperDuper", "STRUCT")
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  ### this doesn't work
  ##plctag = "TestBOOLArray"
  ##value = PLC.ReadStuffs(plctag, 5)
  ##print plctag, value
  
  #plctag = "TestSINTArray"
  #value = PLC.ReadStuffs(plctag, 5)
  #print plctag, value
  
  #plctag = "TestINTArray"
  #value = PLC.ReadStuffs(plctag, 5)
  #print plctag, value
  
  #plctag = "TestDINTArray"
  #value = PLC.ReadStuffs(plctag, 5)
  #print plctag, value
  
  #plctag = "TestREALArray"
  #value = PLC.ReadStuffs(plctag, 5)
  #print plctag, value
  
  #plctag = "TestTIMER.pre"
  #value = PLC.ReadStuffs(plctag)
  #print plctag, value
  
  #plctag = "TestUDT1.Tag"		#DINT
  #value = PLC.ReadStuffs(plctag)
  #print plctag, value
  
  #plctag = "TestUDT2.Tag.Tag"		#DINT
  #value = PLC.ReadStuffs(plctag)
  #print plctag, value
  
  #plctag = "TestUDT3.Tag.Tag.Tag"  	#DINT
  #value = PLC.ReadStuffs(plctag)
  #print plctag, value
  
main()
