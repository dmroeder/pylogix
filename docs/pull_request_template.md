## Short description of change

## Types of changes

<!--- What types of changes does your code introduce? Put an `x` in all the boxes that apply: -->

- [X] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] I have read the **docs/CONTRIBUTING.md** document.
- [X] My code follows the code style of this project.
- [ ] My change requires a change to the documentation.
- [ ] I have updated the documentation accordingly.
- [X] I have read **tests/README.md**.
- [ ] I have added tests to cover my changes.
- [ ] All new and existing tests passed.

## What is the change?
Added misssing esle statement in eip.py / _getPLCTime
-> raw option didn't work
Modified print details in example 21_get_plc_clock.py
-> Wrong returned objects

## What does it fix/add?
Raw value for getting PLC time works now
No more error when using example 21_get_plc_clock.py

## Test Configuration
- PLC Model
Compact Logix L35E & ControlLogix L82E
- PLC Firmware
20.011 & Unknow
- pylogix version
- python version
3.7.3
- OS type and version
Raspberrypi raspbian10
Windows 10
