#! /usr/bin/env /usr/bin/python
import eip as PLC
import sys


def main():
  
  PLC.__init__()			# initialize PLC object
  PLC.IPAddress("192.168.1.10")		# connect to PLC
  
  plctag = "TestBOOL"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestSINT"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestINT"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestDINT"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestREAL"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestSTRING"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  ## this doesn't work
  #plctag = "TestBOOLArray"
  #value = PLC.ReadStuffs(plctag, 5)
  #print plctag, value
  
  plctag = "TestSINTArray"
  value = PLC.ReadStuffs(plctag, 5)
  print plctag, value
  
  plctag = "TestINTArray"
  value = PLC.ReadStuffs(plctag, 5)
  print plctag, value
  
  plctag = "TestDINTArray"
  value = PLC.ReadStuffs(plctag, 5)
  print plctag, value
  
  plctag = "TestREALArray"
  value = PLC.ReadStuffs(plctag, 5)
  print plctag, value
  
  plctag = "TestTIMER.pre"
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestUDT1.Tag"		#DINT
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestUDT2.Tag.Tag"		#DINT
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
  plctag = "TestUDT3.Tag.Tag.Tag"  	#DINT
  value = PLC.ReadStuffs(plctag)
  print plctag, value
  
main()
