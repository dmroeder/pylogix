## Unit Test for Pylogix (CLX, CompactLogix)

In order to ensure code quality, every PR/Commit should ensure that all tests are passed. If the change is covered by tests that are already written then just ensure everything passes and paste results within PR to increase approval.

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

## Adding new tests

It is recommended to create a fixture when the test is easily repeatable by different arguments, then call that from a test. If is something that doesn't need to be repeated more than once, then just do a test.

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

These are default functions from unittest. Change IP, and Slot in setUp when running local tests. Discard changes when done, unless adding something new to the unittest.

## Setting up an RSLogix 5000 Project

Due to the versioning system of Rockwell it is difficult to provide one project for all CLX, and Compactlogix controllers. (Will need someone with an micro800 to do a repeatable test setup as I don't have one of those laying around)

(Files are in the clx_setup folder)

- Import all 3 UDT's (Click on Data Types/User-Defined -> Import)
- Import tags (Tools -> Import -> Tags) (Import controller, then program tags)
- Setup your I/O configuration as per your rack configuration
- Save in a safe spot for next time
- Download test project to PLC, and run unittest.

If for whatever reason your PR is testing something super crazy, then add UDT, and tags but make sure to export new UDTs, and re-export program tags, and controller tags by right clicking in the controller organizer and selecting export tags or Tools/export. Keep in mind the current tags have just about everything so be mindful about adding new tags/udts unless is necessary. As always ask if unsure.

## TODO

- Add Micro800 unittest, and plc setup.
