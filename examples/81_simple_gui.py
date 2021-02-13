'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Create a simple Tkinter window to display discovered devices, tags and a single variable.
Tkinter doesn't come preinstalled on all Linux distributions, so you may need to install it.
For Ubuntu: sudo apt-get install python-tk

Tkinter vs tkinter:
Reference: https://stackoverflow.com/questions/17843596/difference-between-tkinter-and-tkinter
'''

import threading
import socket
import pylogix

from pylogix import PLC

try:
    from Tkinter import *
except ImportError:
    from tkinter import *

class device_discovery_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      discoverDevices()

class get_tags_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      getTags()

class connection_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      comm_check()

class update_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      startUpdateValue()

# startup default values
myTag = 'CT_STRING'
ipAddress = '192.168.1.24'
processorSlot = 3

ver = pylogix.__version__

def main():
    '''
    Create our window and comm driver
    '''
    global root
    global comm
    global checkVar
    global selectedProcessorSlot
    global selectedIPAddress
    global chbMicro800
    global selectedTag
    global connected
    global updateRunning
    global changePLC
    global btnStart
    global btnStop
    global lbDevices
    global lbTags
    global lbConnectionMessage
    global lbErrorMessage
    global tbIPAddress
    global sbProcessorSlot
    global tbTag
    global tagValue
    global popup_menu_tbTag
    global popup_menu_tbIPAddress

    root = Tk()
    root.config(background='black')
    root.title('Pylogix GUI Test')
    root.geometry('800x600')

    connected = False
    updateRunning = True
    changePLC = IntVar()
    changePLC.set(0)

    # bind the "q" keyboard key to quit
    root.bind('q', lambda event:root.destroy())

    # add a frame to hold top widgets
    frame1 = Frame(root, background='black')
    frame1.pack(side=TOP, fill=X)

    # add list boxes for Device Discovery and Get Tags
    lbDevices = Listbox(frame1, height=11, width=45, bg='lightblue')
    lbTags = Listbox(frame1, height=11, width=45, bg='lightgreen')

    lbDevices.pack(anchor=N, side=LEFT, padx=3, pady=3)

    # add a scrollbar for the Devices list box
    scrollbarDevices = Scrollbar(frame1, orient='vertical', command=lbDevices.yview)
    scrollbarDevices.pack(anchor=N, side=LEFT, pady=3, ipady=65)
    lbDevices.config(yscrollcommand = scrollbarDevices.set)

    # copy selected IP Address to the clipboard on the mouse double-click
    # this is currently set to work for IP Address only
    lbDevices.bind('<Double-Button-1>', lambda event: ip_copy())

    # add the Discover Devices button
    btnDiscoverDevices = Button(frame1, text = 'Discover Devices', fg ='green', height=1, width=14, command=start_discover_devices)
    btnDiscoverDevices.pack(anchor=N, side=LEFT, padx=3, pady=3)

    # add a scrollbar for the Tags list box
    scrollbarTags = Scrollbar(frame1, orient='vertical', command=lbTags.yview)
    scrollbarTags.pack(anchor=N, side=RIGHT, padx=3, pady=3, ipady=65)
    lbTags.config(yscrollcommand = scrollbarTags.set)

    # copy selected tag to the clipboard on the mouse double-click
    lbTags.bind('<Double-Button-1>', lambda event: tag_copy())

    lbTags.pack(anchor=N, side=RIGHT, pady=3)

    # add the Get Tags button
    btnGetTags = Button(frame1, text = 'Get Tags', fg ='green', height=1, width=14, command=start_get_tags)
    btnGetTags.pack(anchor=N, side=RIGHT, padx=3, pady=3)

    # add a frame to hold the label for pylogix version and Micro800 checkbox
    frame2 = Frame(root, background='black')
    frame2.pack(fill=X)

    # create a label to show pylogix version
    lblVersion = Label(frame2, text='pylogix v' + ver, fg='grey', bg='black', font='Helvetica 9')
    lblVersion.pack(side=LEFT, padx=3, pady=5)

    # add Micro800 checkbox
    checkVar = IntVar()
    chbMicro800 = Checkbutton(frame2, text="PLC is Micro800", variable=checkVar, command=check_micro800)
    checkVar.set(0)
    chbMicro800.pack(side=RIGHT, padx=5, pady=4)

    # create a label to display the tag value
    tagValue = Label(root, text='~', fg='yellow', bg='navy', font='Helvetica 18', width=52, relief=SUNKEN)
    tagValue.place(anchor=CENTER, relx=0.5, rely=0.5)

    # add button to start updating tag value
    btnStart = Button(root, text = 'Start Update', state='disabled', fg ='blue', height=1, width=10, command=start_update)
    btnStart.place(anchor=CENTER, relx=0.44, rely=0.6)

    # add button to stop updating tag value
    btnStop = Button(root, text = 'Stop Update', state='disabled', fg ='blue', height=1, width=10, command=stopUpdateValue)
    btnStop.place(anchor=CENTER, relx=0.56, rely=0.6)

    # create a label and a text box for the IPAddress entry
    lblIPAddress = Label(root, text='IP Address', fg='white', bg='black', font='Helvetica 8')
    lblIPAddress.place(anchor=CENTER, relx=0.5, rely=0.1)
    selectedIPAddress = StringVar()
    tbIPAddress = Entry(root, justify=CENTER, textvariable=selectedIPAddress)
    selectedIPAddress.set(ipAddress)

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbIPAddress = Menu(tbIPAddress, tearoff=0)
    popup_menu_tbIPAddress.add_command(label='Paste', command=ip_paste)
    tbIPAddress.bind('<Button-3>', lambda event: ip_menu(event, tbIPAddress))

    tbIPAddress.place(anchor=CENTER, relx=0.5, rely=0.13)

    # create a label and a spinbox for the ProcessorSlot entry
    lblProcessorSlot = Label(root, text='Processor Slot', fg='white', bg='black', font='Helvetica 8')
    lblProcessorSlot.place(anchor=CENTER, relx=0.5, rely=0.175)
    selectedProcessorSlot = StringVar()
    sbProcessorSlot = Spinbox(root, width=10, justify=CENTER, from_ = 0, to = 20, increment=1, textvariable=selectedProcessorSlot, state='readonly')
    selectedProcessorSlot.set(processorSlot)
    sbProcessorSlot.place(anchor=CENTER, relx=0.5, rely=0.205)

    # create a label and a text box for the Tag entry
    lblTag = Label(root, text='Tag(s) To Read', fg='white', bg='black', font='Helvetica 8')
    lblTag.place(anchor=CENTER, relx=0.5, rely=0.4)
    selectedTag = StringVar()
    tbTag = Entry(root, justify=CENTER, textvariable=selectedTag, font='Helvetica 11', width=90)
    selectedTag.set(myTag)

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbTag = Menu(tbTag, tearoff=0)
    popup_menu_tbTag.add_command(label='Paste', command=tag_paste)
    tbTag.bind('<Button-3>', lambda event: tag_menu(event, tbTag))

    tbTag.place(anchor=CENTER, relx=0.5, rely=0.44)

    # add a frame to hold connection and error messages listboxes
    frame3 = Frame(root, background='black')
    frame3.pack(side=BOTTOM, fill=X)

    # add a list box for connection messages
    lbConnectionMessage = Listbox(frame3, justify=CENTER, height=1, width=45, fg='blue', bg='lightgrey')
    lbConnectionMessage.pack(anchor=S, side=LEFT, padx=3, pady=3)

    # add a listbox for error messages
    lbErrorMessage = Listbox(frame3, justify=CENTER, height=1, width=45, fg='red', bg='lightgrey')
    lbErrorMessage.pack(anchor=S, side=RIGHT, padx=3, pady=3)

    # add Exit button
    btnExit = Button(root, text = 'Exit', fg ='red', height=1, width=10, command=root.destroy)
    btnExit.place(anchor=CENTER, relx=0.5, rely=0.97)

    comm = PLC()

    start_connection()

    root.mainloop()

    comm.Close()

def start_connection():
    try:
        thread1 = connection_thread()
        thread1.setDaemon(True)
        thread1.start()
    except Exception as e:
        print('unable to start thread1 - connection_thread, ' + str(e))

def start_discover_devices():
    try:
        thread2 = device_discovery_thread()
        thread2.setDaemon(True)
        thread2.start()
    except Exception as e:
        print('unable to start thread2 - device_discovery_thread, ' + str(e))

def start_get_tags():
    try:
        thread3 = get_tags_thread()
        thread3.setDaemon(True)
        thread3.start()
    except Exception as e:
        print('unable to start thread3 - get_tags_thread, ' + str(e))

def start_update():
    try:
        thread4 = update_thread()
        thread4.setDaemon(True)
        thread4.start()
    except Exception as e:
        print('unable to start thread4 - update_thread, ' + str(e))

def check_micro800():
    if checkVar.get() == 1:
        sbProcessorSlot['state'] = 'disabled'
    else:
        sbProcessorSlot['state'] = 'normal'

    changePLC.set(1)
    lbDevices.delete(0, 'end')
    lbTags.delete(0, 'end')
    start_connection()

def discoverDevices():
    lbDevices.delete(0, 'end')

    commDD = PLC()

    try:
        devices = commDD.Discover()
    except:
        commDD.Close()
        commDD = None

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
            i += 1

        for device in devices.Value:
            if device.DeviceID == 14:
                lbDevices.insert(i * 12 + 1, "Modules at " + device.IPAddress)

                '''
                Query each slot for a module
                '''
                with PLC() as c:
                    c.IPAddress = device.IPAddress

                    for j in range(17):
                        x = c.GetModuleProperties(j)
                        lbDevices.insert(i * 12 + 2 + j, "Slot " + str(j) + " " + x.Value.ProductName + " rev: " + x.Value.Revision)

                c.Close()
                c = None

                i += 1

    commDD.Close()
    commDD = None

def getTags():
    lbTags.delete(0, 'end')

    commGT = PLC()
    commGT.IPAddress = selectedIPAddress.get()
    commGT.ProcessorSlot = int(selectedProcessorSlot.get())

    tags = None

    try:
        tags = commGT.GetTagList()
    except:
        commGT.Close()
        commGT = None

    if not tags is None:
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
    else:
        lbTags.insert(1, 'No Tags Retrieved')

    commGT.Close()
    commGT = None

def comm_check():
    global comm
    global connected

    ip = selectedIPAddress.get()
    port = int(selectedProcessorSlot.get())

    if (not connected or comm.IPAddress != ip or comm.ProcessorSlot != port or changePLC.get() == 1):
        comm.Close()
        comm = None
        comm = PLC()
        comm.IPAddress = ip

        if checkVar.get() == 0:
            comm.ProcessorSlot = port
            comm.Micro800 = False
        else:
            comm.Micro800 = True

        lbConnectionMessage.delete(0, 'end')
        lbErrorMessage.delete(0, 'end')

        plcTime = comm.GetPLCTime()

        if plcTime.Value is None:
            if btnStop['state'] == 'disabled':
                btnStart['state'] = 'disabled'
            lbConnectionMessage.insert(1, 'Not Connected')
            lbErrorMessage.insert(1, plcTime.Status)
            connected = False
            root.after(5000, comm_check)
        else:
            lbConnectionMessage.insert(1, 'Connected')
            if btnStop['state'] == 'disabled':
                btnStart['state'] = 'normal'
            connected = True

    changePLC.set(0)

def startUpdateValue():
    global updateRunning
    global connected

    '''
    Call ourself to update the screen
    '''

    if not connected:
        comm_check()

    myTag = selectedTag.get()

    if not updateRunning:
        updateRunning = True
    else:
        if connected:
            # remove all the spaces
            displayTag = (selectedTag.get()).replace(' ', '')

            if displayTag != '':
                myTag = []
                if ',' in displayTag:
                    tags = displayTag.split(',')
                    for tag in tags:
                        if not str(tag) == '':
                            myTag.append(str(tag))
                else:
                    myTag.append(displayTag)

            try:
                response = comm.Read(myTag)
            except:
                response = None

            if not response is None:
                allValues = ''
                for tag in response:
                    allValues += str(tag.Value) + ', '
                tagValue['text'] = allValues[:-2]
            else:
                connected = False
                lbDevices.delete(0, 'end')
                lbTags.delete(0, 'end')

                if response.Status == 'Connection lost':
                    lbConnectionMessage.delete(0, 'end')
                    lbConnectionMessage.insert(1, response.Status)
                    lbErrorMessage.delete(0, 'end')
                    tagValue['text'] = '~'
                else:
                    lbErrorMessage.delete(0, 'end')
                    lbErrorMessage.insert(1, response.Status)
 
            if btnStart['state'] != 'disabled':
                btnStart['state'] = 'disabled'
                btnStop['state'] = 'normal'
                tbIPAddress['state'] = 'disabled'
                if checkVar.get() == 1:
                    sbProcessorSlot['state'] = 'disabled'
                chbMicro800['state'] = 'disabled'
                tbTag['state'] = 'disabled'

        root.after(500, startUpdateValue)

def stopUpdateValue():
    global updateRunning

    if updateRunning:
        updateRunning = False
        tagValue['text'] = '~'
        btnStart['state'] = 'normal'
        btnStop['state'] = 'disabled'
        tbIPAddress['state'] = 'normal'
        chbMicro800['state'] = 'normal'
        if checkVar.get() == 0:
            sbProcessorSlot['state'] = 'normal'
        tbTag['state'] = 'normal'

def tag_copy():
    root.clipboard_clear()
    listboxSelectedTag = (lbTags.get(ANCHOR)).split(" ")[0]
    root.clipboard_append(listboxSelectedTag)

def tag_menu(event, tbTag):
    try:
        old_clip = root.clipboard_get()
    except:
        old_clip = None

    if (not old_clip is None) and (type(old_clip) is str) and tbTag['state'] == 'normal':
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
    try:
        old_clip = root.clipboard_get()
    except:
        old_clip = None

    if (not old_clip is None) and (type(old_clip) is str) and tbIPAddress['state'] == 'normal':
        tbIPAddress.select_range(0, 'end')
        popup_menu_tbIPAddress.post(event.x_root, event.y_root)

def ip_paste():
    # user clicked the "Paste" option so paste the IP Address from the clipboard
    selectedIPAddress.set(root.clipboard_get())
    tbIPAddress.select_range(0, 'end')
    tbIPAddress.icursor('end')

if __name__=='__main__':
    main()
