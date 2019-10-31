# Working with Log Files

Logging is useful to figure out what is going wrong. Using our files example, we'd probably want to log the error instead of printing it.

Time of error is very important, I am using the datetime library for that.

```python
import datetime

now = datetime.datetime.now()
log = open("log.txt", "a+")

# read online value, try, except in case tag doesn't exists
    try:
        value = read_tag(plc_tag)
        put_string = plc_tag + "|" + str(value)

        # append to list
        tags_list.append(put_string)

    except ValueError as e:
        log.write("%s Save Error: %s tag %s %s\n" % (now.strftime("%c"), file_name, plc_tag, e))
        log.flush() # this ensures it logs to the file in the case of a crash
        check_error_log = True # flag to alert user there are errors logged
```

Remember to close the file at the very end of your application.

```
log.close()
```
