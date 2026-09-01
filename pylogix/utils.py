"""
   Copyright 2022 Dustin Roeder (dmroeder@gmail.com)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import math
import re
import struct
import sys


def is_micropython():
    if hasattr(sys, 'implementation'):
        if sys.implementation.name == 'micropython':
            return True
        return False
    return False


def is_python3():
    if hasattr(sys.version_info, 'major'):
        if sys.version_info.major == 3:
            return True
        return False
    return False


def is_python2():
    if hasattr(sys.version_info, 'major'):
        if sys.version_info.major == 2:
            return True
        return False
    return False


def make_standard_string(string, encoding):
    """
    String for Compact/Control Logix
    """
    work = []
    string = string[:82]
    temp = struct.pack('<I', len(string)).decode(encoding)
    for char in temp:
        work.append(ord(char))
    for char in string:
        work.append(ord(char))
    for _ in range(len(string), 84):
        work.append(0x00)
    return work


def make_special_string(string, encoding):
    """
    String for Micro800 and other platforms
    """
    work = []
    temp = struct.pack('<B', len(string)).decode(encoding)
    for char in temp:
        work.append(ord(char))
    for char in string:
        work.append(ord(char))
    return work


def bit_of_word_state(tag, value):
    """
    Find the array/bit element at the end of a tag
    and return whether that bit is true/false in the
    value provided
    ex: (bit 4 of the number 30313 is False)
    """
    bit_pattern = r'\d+$'
    array_pattern = r'\[\s*(0|[1-9][0-9]*)(\s*,\s*(0|[1-9][0-9]*))*\s*\]$'
    try:
        index = re.search(array_pattern, tag).group(0)
        index = index[1:-1]
    except Exception:
        index = re.search(bit_pattern, tag).group(0)

    index = int(index) % 32

    return bit_value(value, index)


def get_word_count(start, length, bits):
    """
    Get the number of words that the requested
    bits would occupy.  We have to take into account
    how many bits are in a word and the fact that the
    number of requested bits can span multiple words.
    """
    new_start = start % bits
    new_end = new_start + length

    total_words = (new_end - 1) / bits
    return int(total_words + 1)


def parse_tag_name(tag):
    """
    Parse the tag name into it's base tag (remove array index and/or
    bit) and get the array index if it exists

    ex: MyTag.Name[42] returns:
    MyTag.Name[42], MyTag.Name, 42
    """
    bit_end_pattern = r'\.\d+$'
    array_pattern = r'\[\s*(0|[1-9][0-9]*)(\s*,\s*(0|[1-9][0-9]*))*\s*\]$'

    # get the array index
    try:
        index = re.search(array_pattern, tag).group(0)
        index = index[1:-1]
        if ',' in index:
            index = index.split(',')
            index = list(map(int, index))
        else:
            index = int(index)
    except Exception:
        index = 0

    # get the base tag name
    base_tag = re.sub(bit_end_pattern, '', tag)
    base_tag = re.sub(array_pattern, '', base_tag)

    return tag, base_tag, index


def bin_to_int(bits, bpw):
    """
    Convert a list of bits to an integer
    """
    sign_limit = 2 ** (bpw - 1) - 1
    conv = (2 ** bpw)

    value = 0
    for bit in reversed(bits):
        value = (value << 1) | bit

    if value > sign_limit:
        value -= conv

    return value


def mod_write_masks(tag, values, bpw):
    """
    The whole goal here is to generate lists of values for modified writes
    (BOOL array or bits of DINT)

    We can only write 32 bits at a time, so we'll take the request from the user
    make the mask lists, then break them up into 4 byte chunks.  Lastly, we'll
    convert them to values.
    """
    bit_pattern = r'\.\d+$'
    array_pattern = r'\[\s*(0|[1-9][0-9]*)(\s*,\s*(0|[1-9][0-9]*))*\s*\]$'

    try:
        # A bit of a word
        index = int(re.search(bit_pattern, tag).group(0)[1:])
    except Exception:
        # boolean arrays
        index = re.search(array_pattern, tag).group(0)
        index = int(index[1:-1])

    # figure out how many words our bits will occupy
    start_bit = index % bpw
    bit_count = len(values)
    word_count = ((start_bit % bpw) + bit_count) / bpw
    word_count = int(math.ceil(word_count))

    # create template high/low mask lists.
    mask_high = [0 for _ in range(word_count * bpw)]
    mask_low = [1 for _ in range(word_count * bpw)]

    # map our values onto our masks
    mask_high[start_bit:start_bit + len(values)] = values
    mask_low[start_bit:start_bit + len(values)] = values

    # split up our lists into chunks of n bytes
    segments_high = [mask_high[x:x + bpw] for x in range(0, len(mask_high), bpw)]
    segments_low = [mask_low[x:x + bpw] for x in range(0, len(mask_low), bpw)]

    # convert our finalized lists of masks to values to be written
    values_high = [bin_to_int(seg, bpw) for seg in segments_high]
    values_low = [bin_to_int(seg, bpw) for seg in segments_low]

    tags = [tag]
    for _ in range(word_count - 1):
        index += bpw
        new_index = "[{}]".format(index)
        new_tag = re.sub(array_pattern, new_index, tag)
        tags.append(new_tag)

    return values_high, values_low, tags


def bit_of_word(tag):
    """
    Test if the user is trying to write to a bit of a word
    ex. Tag.1 returns True (Tag = DINT)
    """
    s = tag.split('.')
    if s[len(s) - 1].isdigit():
        return True
    else:
        return False


def bit_value(value, bit_no):
    """
    Returns the specific bit of a words value
    """
    mask = 1 << bit_no
    if value & mask:
        return True
    else:
        return False
