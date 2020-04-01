# Working with Log Files

Logging is useful to figure out what is going wrong. Using our files example, we'd probably want to log the error instead of printing it.

Time of error is very important, I am using the datetime library for that.

```python
import datetime

now = datetime.datetime.now()
log = open("log.txt", "a+")
check_error_log = False

# read online value
ret = Read(plc_tag)
put_string = ret.TagName + "|" + str(ret.Value)

# Neccesary sanity check, because there are no exceptions with pylogix
if ret.Status == "Success":
    # append to list
    tags_list.append(put_string)

if ret.Status != "Success":
    log.write("%s Save Error: %s tag %s\n" % (now.strftime("%c"), ret.TagName, ret.Status))
    log.flush() # this ensures it logs to the file in the case of a crash
    check_error_log = True # flag to alert user there are errors logged
```

Remember to close the file at the very end of your application.

```
log.close()
```
