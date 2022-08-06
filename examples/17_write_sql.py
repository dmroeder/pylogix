
import pylogix
import time

import mysql.connector

"""
I have a database named pylogix_db, table named recipes
with columns name, number.  Every 5 seconds, we'll read
the tags and update the database with the values/
"""

db_connection = mysql.connector.connect(
                host="localhost",
                user="root",
                passwd="password",
                database = "pylogix_db")

mycursor = db_connection.cursor()
tags = ["recipe_name", "recipe_value"]
comm = pylogix.PLC("192.168.1.10")

def write_to_db(vals):
    """
    Write our values to the database
    """
    cmd = "INSERT INTO recipes (name, number) VALUES (%s, %s)"
    val = (vals[0], vals[1])
    mycursor.execute(cmd, val)
    db_connection.commit()

def read_from_plc():
    """
    Read the defined tags. Return the values as a list
    so tha they are easy to pass to the database.
    """
    ret = comm.Read(tags)

    return [r.Value for r in ret]

run = True
while run:
    try:
        v = read_from_plc()
        write_to_db(v)
        time.sleep(5)

    except KeyboardInterrupt:
        run = False

