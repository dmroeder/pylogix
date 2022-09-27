# pylogix API

Everything with pylogix is done via the PLC module, all the properties and modules will be
discussed beow.  Whether you are reading, writing, pulling the tag list, etc.  To make things
easy for the user, pylogix will automatically make the necessary connection to the PLC when
you call any of the methods.

__Properties:__
- IPAddress (required)
- ProcessorSlot (optional, default=0)
- Micro800 (optional, default=False)
- Route (optional, default=None)
- ConnectionSize (optional, default=4002)
- SocketTimeout (optional, default=5.0)

__Methods:__
- [Read](#read)()
- [Write](#write)()
- [GetTagList](#gettaglist)()
- [GetProgramsList](#getprogramslist)()
- [GetProgramTagList](#getprogramtaglist)()
- [GetPLCTime](#getplctime)()
- [SetPLCTime](#setplctime)()
- [Discover](#discover)()
- [GetModuleProperties](#getmoduleproperties)()
- [GetDeviceProperties](#getdeviceproperties)()

There are a few options for creating an instance of PLC(), how you do it is a matter of style I
suppose.  My preferred method is using contexts, or with statements, but is up to you.
Some options are:

```python
comm = PLC()
comm.IPAddress = "192.168.1.10"
# do stuff
comm.Close()
```
or
```python
comm = PLC("192.168.1.10")
# do stuff
comm.Close()
```
or
```python
with PLC() as comm:
    comm.IPAddress = "192.168.1.10"
    # do stuff
```
my preferred
```python
with PLC("192.168.1.10") as comm:
    # do stuff
```

Again, how you do it is up to you, each method works.  There are some things to consider:

1. Don't call Close() unnecessarily.  If the PLC no longer sees a request, it will eventually
flush the connection, after about 90 seconds. So if you are reading/writing more often than
90 seconds, don't call Close(), just keep reading, call Close() when your program exits

2. With statements will automatically call Close() when the indent returns.  It's a common
issue where people write their with statement within a loop.  Doing this will open and
close the connection with each iteration of the loop.  Instead, write the loop inside the
with statement, that way, the driver is declared first, then the loop performs the actions.

3. When using with threads, be sure to create an instance for each thread, as opposed to sharing
the instance between threads

NO:
```python
while True:
    with PLC("192.168.1.10") as comm:
        # no no
```
YES:
```python
with PLC("192.168.1.10") as comm:
    while True:
        # ahhh, much better
```

All pylogix methods will return the data in as the
[Response](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_response.py) class,
which has 3 members: TagName, Value and Status.  Not all members apply to every method, so there
are occasions where TagName, for example, will be None.  Like when getting the PLC time, TagName
doesn't apply.  Value's type varies depending which method is being used.  For example, Value can
be a single value when reading a single tag, or can be a list of values when reading a list of tags.
Or Value can be the lgx_device type, when requesting device properties or discovering devices on the
network
```python
ret = comm.Read("MyTag")
print(ret.TagName, ret.Value, ret.Status)
```

__IPAddress__
Straight forward, this is the PLC's IP Address, as a string.  Or, for ControlLogix, the
Ethernet module you will be accessing the PLC at.
>comm.IPAddress = "172.17.130.11"

__ProcessorSlot__
Integer for which slot the processor is in.  By default, the value is 0, since it is most
common for a processor to be in slot 0.  For CompactLogix and Micro8xx, this is always true.
For ControlLogix, the processor can be in any slot.  In fact, you can have multiple processors
in one chassis.
>comm.ProcessorSlot = 4 # connect to controller in slot 4

__Micro800__
True/False property, False by default.  The Micro820/850's support Ethernet I/P, but use a
slightly different path, so the driver needs to know this up front.  Set to True when accessing
a Micro800 PLC's.
>comm.Micro800 = True

Keep in mind, these PLC's are pretty feature limited, so not all pylogix methods will work with
them.

__Route__
Route allows you to bridge to other controllers through a ControlLogix backplane or 5380 controller
in dual IP mode.  Routes are always in pairs of tuples.  An example:
>comm.Route = [(1,4), (2, '10.10.10.9')]

__NOTE:__ Routing has always been a feature of ControlLogix, so the value of going out of an Ethernet
port has always been 2. That is, until the 5380 CompactLogix and dual IP mode came along.  You use
a value of  3 or 4, depending on which port you are going out of.

__ConnectionSize__
pylogix, as it currently is, will make an attempt to connect at the maximum possible connection
size, which is 4002 bytes.  If unsuccessful, it will attempt at the next common max size, which
is 508 bytes.  The user can specify a connection size anywhere in between.  The best practice is
to leave this value at default.  The main reason for making this configurable is a history
problem.  pylogix made this configurable originally.  Later, the concept of default to the max
size, then fall back another size was implemented.  Making it configurable made sure that there
was no compatibility issues.

There is no known benefit to reducing the connection size.  In fact, you will get the best
performance by leaving it at the max.  There seems to be no latency issue with always using the
larger packet size.

The early controllers and Ethernet modules supported connection sizes of 508 bytes.  At around
v18, Rockwell implemented connection sizes of 4002 bytes.

__SocketTimeout__
If pylogix cannot connect to a PLC or loses its connection to the PLC, the default timeout is
5 seconds (5.0). If this time is too long, it can be lowered.  Just be sure to not set it lower
than the time it takes the PLC to reply to prevent false timeouts.  PLC's typically respond
in a few milliseconds, but that is not guaranteed.

# Read
Read allows you to pull values from the PLC using tag names.  You can perform simple reads using
single tag names, or bundle reads using lists of tags names.  Read is only currently capable of
handling the fundamental data types (BOOL, SINT, INT, DINT, LINT, REAL, STRING). While you can
read members of UDT's, it must be at the fundamental data type level.  This method will currently
return the raw bytes of the UDT values, which you will have to parse.

While it is necessary for pylogix to know the data type of the tag being read, to make it simple
for the user, pylogix will discover the data type the very first time a tag is accessed.  The data
type is saved in a dict KnownTags so that this only has to happen once per new tag.  This does cause
some extra overhead and can impact performance a bit, especially if you are just reading a large number
of unique tags, then closing.  To help, you can provide the data type up front, which will skip the
discovery of the data type.

__NOTE:__ if you want to access program scoped tags, use the following syntax
>Program:ProgramName.TagName

#### Single tag reads
To read a single tag, provide a tag name and a single instance of the response class will be
returned.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    ret = comm.Read("MyDint")
    print(ret.TagName, ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyDint 8675309 Success
```
</p>
</details>

#### Read an array
To read an array, provide a tag name and the number of elements you want to read.  Value in
the response will be a list of the values you requested.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    ret = comm.Read("MyDintArray[0]", 10)
    print(ret.TagName, ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyDintArray[0] [42, 43, 44, 45, 46, 47, 48, 49, 50, 51] Success
```
</p>
</details>

#### Read a list of tags
The best way to improve performance is to read tags in a list. Reading lists of tags will take
advantage of the mulit-service request, packing many request into a single packet.  When reading
lists, a list of the Response class will be returned.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    tags = ["MyDint", "MyString", "MyInt"]
    ret = comm.Read(tags)

    # print exactly how the data is returned
    print("returned data", ret)

    # print each item returned
    for r in ret:
        print(r.TagName, r.Value, r.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
returned data [Response(TagName=MyDint, Value=8675309, Status=Success), Response(TagName=MyString, Value=I am a string, Status=Success), Response(TagName=MyInt, Value=90, Status=Success)]
MyDint 8675309 Success
MyString I am a string Success
MyInt 90 Success
```
</p>
</details>

#### Skip the data type discovery
While I prefer to keep things simple and let pylogix get the data type for me, you can bypass this
feature to get a little better performance.  The data type discovery only happens once per tag, so
if you are reading in a loop, this doesn't have much benefit.  But of you are reading a large list of
tags, it can speed things up.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    ret = comm.Read("MyDint", datatype=0xc4)
    print(ret.TagName, ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyDint 8675309 Success
```
</p>
</details>


# Write
Use Write() to write values to PLC tags. You can write a value to a single tag, a list of values to an
array tag or write a list of values to a list of tags. Write will return the Response class, which is
mainly useful for the status to see if your write was successful or not.

#### Write a single value
To write a single value to a single tag, pass a tag name and a value. Be mindful of the data type, for
integers (SINT/INT/DINT) use the int type for the value, for REAL, use the float type and for strings,
use the str type.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    ret = comm.Write("MyDint", 10)
    print(ret.TagName, ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyDint 10 Success
```
</p>

<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    ret = comm.Write("MyString", "I am a string")
    print(ret.TagName, ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyString I am a string Success
```
</p>

</details>


#### Write list of values
You can write a list of values to an array by passing a list of values.  You don't have to specify the
length, pylogix will simply use the number of values in the list.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    values = [123, 456, 789]
    ret = comm.Write("MyDintArray[0]", values)
    print(ret.TagName, ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyDintArray[0] [123, 456, 789] Success
```
</p>
</details>


#### Write multiple tags at once
Similar to Read, you can write multiple tags in one request.  Pylogix will use the multi-service request
and pack the requests into the minimum number of packets.  You make a list, where each write is a tuple
containing the tag name and the value.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    request = [("MyDint", 10), ("MyInt", 3), ("MyString", "hello world")]
    ret = comm.Write(request)
    for r in ret:
        print(r.TagName, r.Value, r.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
MyDint 10 Success
MyInt 3 Success
MyString hello world Success
```
</p>
</details>


# GetTagList
Retreives the controllers tag list, including program scoped tags (default).  Returns the Response class,
where the Value will be a list of [Tag](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_tag.py)
class.  pylogix also saves this list internally in TagList.  Along with the tag list, pylogix also retrieves
the UDT definitions, which are stored as a dict in UDT.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    tags = comm.GetTagList()
    for t in tags.Value:
        print("Tag:", t.TagName, t.DataType)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
Tag: Program:MainProgram
Tag: MyDint DINT
Tag: MyDintArray DINT
Tag: MyString STRING
Tag: MyInt INT
Tag: MyUDT Pylogix
```
</p>
</details>

# GetProgramsList
Retrieves only a list of the program names.  This will automatically call GetTagList in order to get the list
of program names.  Only a list of the program names will be returned.  This can be useful if you want to only
get a list of a particular programs tag list.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    programs = comm.GetProgramsList()
    print(programs.Value)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
['Program:WidgetProgram', 'Program:ThingyProgram']
```
</p>
</details>


# GetProgramTagList
Retrieves a list of a particular program.  Requires a program name to be provided.  Returns the Response class
where the Value will be a list of [Tag](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_tag.py) class.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    program_tags = comm.GetProgramTagList("Program:WidgetProgram")
    for t in program_tags.Value:
        print("Tag:", t.TagName, t.DataType)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
('Tag:', 'Program:WidgetProgram.WidgetDint', 'DINT')
```
</p>
</details>


# GetPLCTime
Reads the PLC clock, returns the Response class, by default, Value will be the datetime class.  Optionally,
if you set raw=True, the raw microseconds will be returned.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    time = comm.GetPLCTime()
    print("PLC Time:", time.Value)

    raw_time = comm.GetPLCTime(True)
    print("Raw Time:", raw_time.Value)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
PLC Time: 2021-04-20 15:41:22.964380
Raw Time: 1618933282970171
```
</p>
</details>


# SetPLCTime
Synchronizes  the PLC clock with your computers time.  This is similar to what happens when you ae online with
a controller and click Set Date, Time and Zone from Workstation, in Controller Properties of RSLogix5000 or
Studio5000 Logix Designer.  Returns the Response class, which is mainly useful for the status.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    ret = comm.SetPLCTime()
    print(ret.Value, ret.Status)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
1618958684216474 Success
```
</p>
</details>

# Discover
Sends a broadcast request out on the network, which all Ethernet I/P devices listen for and respond with basic
information about themselves.  All Ethernet I/P devices are required to support this feature.  This is what
RSLinx uses in its Ethernet I/P driver to discover devices on the network.  Returns the Response class,
Value will be the [Device](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_device.py) class.

__NOTE:__ Because all Ethernet I/P devices are designed to respond to this, many think that pylogix will be
able to communicate with 3rd party devices in some meaningful way.  The CIP objects targeted by pylogix are
Rockwell specific objects, not part of the ODVA spec.  The CIP spec allows for vendor specific object.  While
there may be devices out there that support the same objects, I only have access to Rockwell PLC's, so I have
no way to support them.  I can offer no support for them.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    devices = comm.Discover()
    for device in devices.Value:
        print(device.ProductName, device.Revision)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
1769-L30ER/A LOGIX5330ER 30.11
5069-L310ER/A 32.12
```
</p>
</details>

# GetModuleProperties
Requests properties of a specific module.  Requires a slot to be specified.  This method is useful for querying
devices that are in a chassis.  Like local I/O in a CompactLogix chassis, or even modules in a Point I/O chassis.
Returns the Response class, where Value is the [Device](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_device.py) class.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    device = comm.GetModuleProperties(3).Value
    print(device.ProductName, device.Revision)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
1734-IB8 8 PT 24VDC SINK IN 3.31
```
</p>
</details>

# GetDeviceProperties
Similar to GetModuleProperties, this queries a device at an IP address.  This is useful for querying things that
are not part of a chassis, like PowerFlex drives, or maybe a barcode reader that supports Ethernet I/P.  Returns
the Response class, where Value is the [Device](https://github.com/dmroeder/pylogix/blob/master/pylogix/lgx_device.py) class.

<details><summary>Example</summary>
<p>

```python
from pylogix import PLC
with PLC("192.168.1.9") as comm:
    device = comm.GetDeviceProperties().Value
    print(device.ProductName, device.Revision)
```
result:
```console
pylogix@pylogix-kde:~$ python3 example.py
1769-L30ER/A LOGIX5330ER 30.11
```
</p>
</details>

# Additional information

When reading/writing, pylogix keeps a dict called KnownTags, this is used to store the tag name
and data type for the purpose of not having to request this each time a tag is read or written
to.  There are users who read a list of 1000 or more unique tag names, retrieving the data type
essentially doubles the time that it would take to read the values.  While the performance has
increased drastically in this case by utilizing the mult-service request to retrieve the data
type.  Still, there ae users that want maximum performance, so Read/Write allows providing the
data type up front.  Doing this adds the tag name and data type to the KnownTags dict up front,
then skips the initial exchange. You can see the atomic data type values by printing the CIPTypes
dict:
>print(comm.CIPTypes)

When requesting the PLC's tag list, there is also a dict that is saved of the UDT definitions
called UDT.  This will be the Tag type, which contains a lot of properties.  After reading the
tag list, you can print this dict:
>print(comm.UDT)
