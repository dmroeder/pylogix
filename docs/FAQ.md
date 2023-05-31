# Frequent Asked Questions

1. Does pylogix work with PLC5, SLC, MicroLogix?
   No

2. Does pylogix work with emulate? Yes, locally only. Ensure ProcessorSlot is set to 2

3. Does pylogix work with softlogix? Yes, locally and remote. Ensure ProcessorSlot is set to 2

4. Does pylogix work with Micro8xx, and CCW Simulator? Yes

5. Can pylogix read Micro8xx program tags? No, it can only read global tags.

6. Does pylogix works with other brand PLCs, such as Omron, Siemens, etc? No

7. Does pylogix support custom path routing? Yes

8. Does pylogix support reading from multiple PLCs? Yes, create multiple PLC object instances

9. What PLC models does pylogix support? CompactLogix, ControlLogix, Micro8xx

10. How can I install pylogix? Installation can be done primarily with pip, or local install. Instructions on README

11. Does pylogix support UDT's structure read? Yes, and no. You can get a read in raw bytes which you'll then need to know how to unpack yourself example of that [here](https://github.com/dmroeder/pylogix/blob/master/examples/40_read_timer.py). There is no way to read the structure of the UDT at the moment discussion [here](https://github.com/dmroeder/pylogix/issues/67). There's also no current way to write raw to UDT's.
