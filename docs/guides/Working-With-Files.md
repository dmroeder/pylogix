## Working with Files

It is pretty useful to have configuration files with given tags for read/write.

### To read all lines from a file:

tags.txt

```
tag_01
tag_02
tag_03
...
```

```python

file_extension = txt

with open(path + "\\" + file + "." + file_extension) as f:
        all_lines = f.readlines()
```

### To write tags to a file:

saved_tags.txt

First append tags to a list:

```python
# read online value, try, except in case tag doesn't exists
    try:
        value = read_tag(plc_tag)
        put_string = plc_tag + "|" + str(value)

        # append to list
        tags_list.append(put_string)

    except ValueError as e:
        print(e)
```

Then save to a file:

```python
with open(path + "\\" + file + "_Save." + file_extension, "w") as dp_save_file:
        dp_save_file.writelines(tags_list)
```
