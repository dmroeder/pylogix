'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Create a simple Tkinter window to display discovered devices,
tags and a single variable.
Tkinter doesn't come preinstalled on all
Linux distributions, so you may need to install it.
For Ubuntu: sudo apt-get install python-tk

Tkinter vs tkinter - Reference: https://stackoverflow.com/questions/17843596/difference-between-tkinter-and-tkinter
'''

from pylogix import PLC

try:
    from Tkinter import *
except ImportError:
    from tkinter import *

myTag = 'CT_STRING'
ipAddress = '192.168.1.24'
processorSlot = 3

def main():
    '''
    Create our window and comm driver
    '''
    global root
    global comm
    global tagValue
    global selectedProcessorSlot
    global selectedIPAddress
    global selectedTag
    global updateRunning
    global btnStart
    global btnStop
    global lbDevices
    global lbTags
    global tbIPAddress
    global sbProcessorSlot
    global tbTag
    global popup_menu_tbTag
    global popup_menu_tbIPAddress

    root = Tk()
    root.config(background='black')
    root.title('Pylogix GUI Test')
    root.geometry('800x600')

    comm = PLC()

    updateRunning = True

    # bind the "q" keyboard key to quit
    root.bind('q', lambda event:root.destroy())

    # add Exit button
    btnExit = Button(root, text = 'Exit', fg ='red', height=1, width=10, command=root.destroy)
    btnExit.pack(side=BOTTOM, pady=5)

    # add button to start updating tag value
    btnStart = Button(root, text = 'Start Update', state='normal', fg ='blue', height=1, width=10, command=startUpdateValue)
    btnStart.place(anchor=CENTER, relx=0.44, rely=0.6)

    # add button to stop updating tag value
    btnStop = Button(root, text = 'Stop Update', state='disabled', fg ='blue', height=1, width=10, command=stopUpdateValue)
    btnStop.place(anchor=CENTER, relx=0.56, rely=0.6)

    # add list boxes for Devices and Tags
    lbDevices = Listbox(root, height=11, width=45, bg='lightblue')
    lbTags = Listbox(root, height=11, width=45, bg='lightgreen')

    lbDevices.pack(anchor=N, side=LEFT, padx=3, pady=3)

    # add scrollbar for the Devices list box
    scrollbarDevices = Scrollbar(root ,orient="vertical", command=lbDevices.yview)
    scrollbarDevices.pack(anchor=N, side=LEFT, pady=3, ipady=65)
    lbDevices.config(yscrollcommand = scrollbarDevices.set)

    # copy selected IP Address to the clipboard on the mouse double-click
    # this is currently set to work for IP Address only
    lbDevices.bind('<Double-Button-1>', lambda event: ip_copy())

    # add Discover Devices button
    btnDiscoverDevices = Button(root, text = 'Discover Devices', fg ='brown', height=1, width=14, command=discoverDevices)
    btnDiscoverDevices.pack(anchor=N, side=LEFT, padx=3, pady=3)

    # add scrollbar for the Tags list box
    scrollbarTags = Scrollbar(root ,orient="vertical", command=lbTags.yview)
    scrollbarTags.pack(anchor=N, side=RIGHT, padx=3, pady=3, ipady=65)
    lbTags.config(yscrollcommand = scrollbarTags.set)

    # copy selected tag to the clipboard on the mouse double-click
    lbTags.bind('<Double-Button-1>', lambda event: tag_copy())

    lbTags.pack(anchor=N, side=RIGHT, pady=3)

    # add Get Tags button
    btnGetTags = Button(root, text = 'Get Tags', fg ='brown', height=1, width=14, command=getTags)
    btnGetTags.pack(anchor=N, side=RIGHT, padx=3, pady=3)

    # create a label to display our variable
    tagValue = Label(root, text='Tag Value', fg='yellow', bg='navy', font='Helvetica 24', width=24)
    tagValue.place(anchor=CENTER, relx=0.5, rely=0.5)

    # create a label and a text box for the IPAddress entry
    lblIPAddress = Label(root, text='IP Address', fg='white', bg='black', font='Helvetica 8')
    lblIPAddress.place(anchor=CENTER, relx=0.5, rely=0.12)
    selectedIPAddress = StringVar()
    tbIPAddress = Entry(root, justify=CENTER, textvariable=selectedIPAddress)
    selectedIPAddress.set(ipAddress)

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbIPAddress = Menu(tbIPAddress, tearoff=0)
    popup_menu_tbIPAddress.add_command(label='Paste', command=ip_paste)
    tbIPAddress.bind('<Button-3>', lambda event: ip_menu(event, tbIPAddress))

    tbIPAddress.place(anchor=CENTER, relx=0.5, rely=0.15)

    # create a label and a spinbox for the ProcessorSlot entry
    lblProcessorSlot = Label(root, text='Processor Slot', fg='white', bg='black', font='Helvetica 8')
    lblProcessorSlot.place(anchor=CENTER, relx=0.5, rely=0.22)
    selectedProcessorSlot = StringVar()
    sbProcessorSlot = Spinbox(root, width=10, justify=CENTER, from_ = 0, to = 20, increment=1, textvariable=selectedProcessorSlot, state='readonly')
    selectedProcessorSlot.set(processorSlot)
    sbProcessorSlot.place(anchor=CENTER, relx=0.5, rely=0.25)

    # create a label and a text box for the Tag entry
    lblTag = Label(root, text='Tag To Poll', fg='white', bg='black', font='Helvetica 8')
    lblTag.place(anchor=CENTER, relx=0.5, rely=0.38)
    selectedTag = StringVar()
    tbTag = Entry(root, justify=CENTER, textvariable=selectedTag, font='Helvetica 10', width=90)
    selectedTag.set(myTag)

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbTag = Menu(tbTag, tearoff=0)
    popup_menu_tbTag.add_command(label='Paste', command=tag_paste)
    tbTag.bind('<Button-3>', lambda event: tag_menu(event, tbTag))

    tbTag.place(anchor=CENTER, relx=0.5, rely=0.42)

    discoverDevices()
    getTags()

    root.mainloop()
    comm.Close()

def discoverDevices():
    lbDevices.delete(0, 'end')

    devices = comm.Discover()

    if str(devices) == 'None [] Success':
        lbDevices.insert(1, 'No Devices Discovered')
    else:
        i = 0
        for device in devices.Value:
            lbDevices.insert(i * 12 + 1, 'IP Address: ' + device.IPAddress)
            lbDevices.insert(i * 12 + 2, 'Product Name: ' + device.ProductName)
            lbDevices.insert(i * 12 + 3, 'Product Code: ' + str(device.ProductCode))
            lbDevices.insert(i * 12 + 4, 'Vendor: ' + device.Vendor)
            lbDevices.insert(i * 12 + 5, 'Vendor ID: ' + str(device.VendorID))
            lbDevices.insert(i * 12 + 6, 'Device Type: ' + str(device.DeviceType))
            lbDevices.insert(i * 12 + 7, 'Device ID: ' + str(device.DeviceID))
            lbDevices.insert(i * 12 + 8, 'Revision: ' +  device.Revision)
            lbDevices.insert(i * 12 + 9, 'Serial: ' + device.SerialNumber)
            lbDevices.insert(i * 12 + 10, 'State: ' + str(device.State))
            lbDevices.insert(i * 12 + 11, 'Status: ' + str(device.Status))
            lbDevices.insert(i * 12 + 12, '----------------------------------')
            i = i + 1

def getTags():
    global comm

    lbTags.delete(0, 'end')

    comm_check()

    tags = comm.GetTagList()

    if not tags.Value is None:
        for t in tags.Value:
            j = 1
            if t.DataType == '':
                lbTags.insert(j, t.TagName)
            else:
                lbTags.insert(j, t.TagName + ' (DataType - ' + t.DataType + ')')
            j = j + 1
    else:
        lbTags.insert(1, 'No Tags Retrieved')

def comm_check():
    global comm

    ip = selectedIPAddress.get()
    port = int(selectedProcessorSlot.get())

    if (comm.IPAddress != ip or comm.ProcessorSlot != port):
        comm.Close()
        comm = None
        comm = PLC()
        comm.IPAddress = ip
        comm.ProcessorSlot = port

def startUpdateValue():
    global updateRunning

    '''
    Call ourself to update the screen
    '''

    comm_check()

    myTag = selectedTag.get()

    if not updateRunning:
        updateRunning = True
    else:
        if myTag != "":
            tagValue['text'] = comm.Read(myTag).Value
            root.after(500, startUpdateValue)
            btnStart['state'] = 'disabled'
            btnStop['state'] = 'normal'
            tbIPAddress['state'] = 'disabled'
            sbProcessorSlot['state'] = 'disabled'
            tbTag['state'] = 'disabled'

def stopUpdateValue():
    global updateRunning
   
    if updateRunning:
        updateRunning = False
        tagValue['text'] = 'Tag Value'
        btnStart['state'] = 'normal'
        btnStop['state'] = 'disabled'
        tbIPAddress['state'] = 'normal'
        sbProcessorSlot['state'] = 'normal'
        tbTag['state'] = 'normal'

def tag_copy():
    root.clipboard_clear()
    listboxSelectedTag = (lbTags.get(ANCHOR)).split(" ")[0]
    root.clipboard_append(listboxSelectedTag)

def tag_menu(event, tbTag):
    if root.clipboard_get() != "" and tbTag['state'] == 'normal':
        tbTag.select_range(0, 'end')
        popup_menu_tbTag.post(event.x_root, event.y_root)

def tag_paste():
    # user clicked the "Paste" option so paste the tag from the clipboard
    selectedTag.set(root.clipboard_get())
    tbTag.select_range(0, 'end')
    tbTag.icursor('end')

def ip_copy():
    if (lbDevices.get(ANCHOR)).split(" ")[0] == "IP":
        root.clipboard_clear()
        listboxSelectedIPAddress = (lbDevices.get(ANCHOR)).split(" ")[2]
        root.clipboard_append(listboxSelectedIPAddress)

def ip_menu(event, tbIPAddress):
    if root.clipboard_get() != "" and tbIPAddress['state'] == 'normal':
        tbIPAddress.select_range(0, 'end')
        popup_menu_tbIPAddress.post(event.x_root, event.y_root)

def ip_paste():
    # user clicked the "Paste" option so paste the IP Address from the clipboard
    selectedIPAddress.set(root.clipboard_get())
    tbIPAddress.select_range(0, 'end')
    tbIPAddress.icursor('end')

if __name__=='__main__':
    main()
