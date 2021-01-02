## Unit Test for Pylogix (CLX, CompactLogix)

In order to ensure code quality, every PR/Commit should ensure that all tests are passed. If the code change is covered by tests that are already written then just ensure everything passes and paste results within PR to increase approval.

Output sample:

```
test_array (PylogixTests.PylogixTests) ... ok
test_basic (PylogixTests.PylogixTests) ... ok
test_combined (PylogixTests.PylogixTests) ... ok
test_discover (PylogixTests.PylogixTests) ... ok
test_get_tags (PylogixTests.PylogixTests) ... ok
test_multi_read (PylogixTests.PylogixTests) ... ok
test_time (PylogixTests.PylogixTests) ... ok
test_udt (PylogixTests.PylogixTests) ... ok

----------------------------------------------------------------------
Ran 8 tests in 5.691s

OK
```

## Video Demo

[![Demo](https://img.youtube.com/vi/RCHo5xJQIlg/0.jpg)](https://www.youtube.com/watch?v=RCHo5xJQIlg)

## Adding new tests

The followings paths should guide you when deciding to create new tests:

- Fix a bug, for an existing test (Use PylogixTests.py)
- Fix a bug, for a non existing test, with a basic PLC setup. (Use PylogixTests.py)
- Adding a new feature, with a basic PLC setup (Use PylogixTests.py)
- Adding a new feature, with a difficult PLC setup. i.e. not easy to reproduce. (See folder structure below)

It is recommended to create a fixture when the test is easily repeatable by different arguments following (DRY) concepts, then call that fixture from a test. If is something that doesn't need to be repeated more than once, then just do a test.

If is something that is hard to setup then do a complete unittest class, and add a Results.txt with passed tests. This will ensure the code works, but at the same time not add extra tests to the basic tests PylogixTests.py. In the end most code should be easy to test, but is understandable to add custom code once proven it works.

Sample new feature folder tree with difficult setup:

```
tests/
   |
   -- NewFeatureNameTests/
     |__ NewFeatureNameTests.py
     |__ NewFeatureNameResults.txt

```

Sample fixture:

```
def udt_array_fixture(self, prefix=""):
# test code
# assertion
...
```

Sample test:

```
def test_array(self, prefix=""):
    self.udt_array_fixture()
    self.udt_array_fixture('Program:MainProgram.p')
...
```

In addition to fixtures, and tests, you can add helper methods, if is one or two then just add within the PylogixTests class just don't put keyword `test` within the function name, otherwise separate into is own class, see Randomizer example within this Tests folder.

## setUp and tearDown

These are default functions from unittest, they will run before each test.

## Setup test configuration

I've added a `.gitignore` entry for plc configurations in order to avoid having to keep discarding ip, slot changes inside pylogixTests.py.

Inside the tests folder create a file `plcConfig.py`, then copy and paste below variables:

```
plc_ip = '192.168.0.26'
plc_slot = 1
isMicro800 = False
```

## Setting up an RSLogix 5000 Project

Due to the versioning system of Rockwell it is difficult to provide one project for all CLX, and Compactlogix controllers. (Will need someone with an micro800 to do a repeatable test setup as I don't have one of those laying around)

(Files are in the clx_setup folder)

- Import all 3 UDT's (Click on Data Types/User-Defined -> Import)
- Import tags (Tools -> Import -> Tags) (Import controller, then program tags)
- Setup your I/O configuration as per your rack configuration
- Save in a safe spot for next time
- Download test project to PLC, and run unittest.

If for whatever reason your PR is testing something super crazy, then add UDT, and tags but make sure to export new UDTs, and re-export program tags, and controller tags by right clicking in the controller organizer and selecting export tags or Tools/export. Keep in mind the current tags have just about everything so be mindful about adding new tags/udts unless is necessary. As always ask if unsure.

## Tox Integration

The project also leverages tox testing since it supports py2, and every change must be checked against py2 and py3.

To run tox, install tox in your preferred python version, then run tox:

```
pip install tox
tox
```

## TODO

- Create a micro800 project, and export tags
- Conform `pylogixTests.py` to micro800 based on functions that work with that plc
- Have the community run the test on micro800
