"""
Create a simple Tkinter window to display a
single variable.

Tkinter doesn't come preinstalled on all
Linux distributions, so you may need to install it.

For Ubuntu: sudo apt-get install python-tk
"""
from pylogix import PLC

try:
    from Tkinter import *
except ImportError:
    from tkinter import *

tag_name = 'BaseDINT'
ip_address = '192.168.1.10'

root = Tk()
comm = PLC()
comm.IPAddress = ip_address
production_count = Label(root, text='n', fg='white', bg='black', font='Helvetica 350 bold')


def main():
    """
    Create our window and comm driver
    """
    # create a tkinter window
    root.config(background='black')
    root.title = 'Production Count'
    root.geometry('800x600')
    
    # bind the "q" key to quit
    root.bind('q', lambda event: root.destroy())
    
    # create a label to display our variable
    production_count.place(anchor=CENTER, relx=0.5, rely=0.5)
    
    # call our updater and show our window
    root.after(1000, update_value)
    root.mainloop()
    comm.Close()


def update_value():
    """
    Call ourselves to update the screen
    """
    production_count['text'] = comm.Read(tag_name).Value
    root.after(500, update_value)


if __name__ == '__main__':
    main()
