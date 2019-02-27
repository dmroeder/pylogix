'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Create a simple Tkinter window to display a
single variable.

Tkinter doesn't come preinstalled on all
Linux distributions, so you may need to install it.

For Ubuntu: sudo apt-get install python-tk
'''
from pylogix import PLC
from Tkinter import *

tagName = 'Time.Second'
ipAddress = '192.168.1.9'

def main():
    '''
    Create our window and comm driver
    '''
    global root
    global comm
    global ProductionCount
    
    # create a comm driver
    comm = PLC()
    comm.IPAddress = ipAddress

    # create a tkinter window
    root = Tk()
    root.config(background='black')
    root.title = 'Production Count'
    root.geometry('800x600')
    
    # bind the "q" key to quit
    root.bind('q', lambda event:root.destroy())
    
    # create a labe to display our variable
    ProductionCount = Label(root, text='n', fg='white', bg='black', font='Helvetica 350 bold')
    ProductionCount.place(anchor=CENTER, relx=0.5, rely=0.5)
    
    # call our updater and show our window
    root.after(1000, UpdateValue)
    root.mainloop()
    comm.Close()

def UpdateValue():
    '''
    Call ourself to update the screen
    '''
    ProductionCount['text'] = comm.Read(tagName) 
    root.after(500, UpdateValue)

if __name__=='__main__':
    main()

