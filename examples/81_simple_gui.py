# See screenshots here: https://github.com/dmroeder/pylogix/issues/156

# This example allows reading either a single tag or multiple tags separated by semicolon (';').
# Single tag example: CT_2D_DINTArray[0,0] or CT_STRING or CT_BOOLArray[252].
# Multi tag example: CT_DINT; CT_REAL; CT_3D_DINTArray[0,3,1].

# It also allows reading multiple elements of an array with the following tag format: tagName[x]{y}
# where 'x' is the starting array index(es) and 'y' is the number of consecutive elements to read.
# This has to be entered as a single tag, example: CT_REALArray[0]{15} or CT_DINTArray[0,1,0]{7}

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
import pylogix
import datetime

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
myTag, ipAddress, processorSlot = ['CT_STRING', 'CT_REAL', 'CT_DINT'], '192.168.1.20', 3

ver = pylogix.__version__

def main():
    '''
    Create our window and comm driver
    '''
    global root
    global comm
    global checkVar
    global checkVarSaveTags
    global checkVarLogTagValues
    global selectedProcessorSlot
    global selectedIPAddress
    global chbMicro800
    global selectedTag
    global connected
    global updateRunning
    global connectionInProgress
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
    global popup_menu_save_tags_list

    root = Tk()
    root.config(background='black')
    root.title('Pylogix GUI Test')
    root.geometry('800x600')

    connectionInProgress, connected, updateRunning = False, False, True

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

    # add 'Log tag values' checkbox
    checkVarLogTagValues = IntVar()
    chbLogTagValues = Checkbutton(frame2, text="Log tag(s) values", variable=checkVarLogTagValues)
    checkVarLogTagValues.set(0)
    chbLogTagValues.pack(side=LEFT, padx=95, pady=4)

    # add Micro800 checkbox
    checkVar = IntVar()
    chbMicro800 = Checkbutton(frame2, text="PLC is Micro800", variable=checkVar, command=check_micro800)
    checkVar.set(0)
    chbMicro800.pack(side=RIGHT, padx=5, pady=4)

    # add 'Save tags' checkbox
    checkVarSaveTags = IntVar()
    chbSaveTags = Checkbutton(frame2, text="Save tags list", variable=checkVarSaveTags)
    checkVarSaveTags.set(0)
    chbSaveTags.pack(side=RIGHT, padx=80, pady=4)

    # add the "Paste" menu on the mouse right-click
    popup_menu_save_tags_list = Menu(chbSaveTags, bg='lightblue', tearoff=0)
    popup_menu_save_tags_list.add_command(label='Click the Get Tags button to save the list')
    chbSaveTags.bind('<Button-1>', lambda event: save_tags_list(event, chbSaveTags))

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
    selectedTag.set((str(myTag).replace(',', ';'))[1:-1].replace('\'', ''))

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

    if not comm is None:
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
    except:
        commDD.Close()
        commDD = None

def getTags():
    lbTags.delete(0, 'end')

    commGT = PLC()
    commGT.IPAddress = selectedIPAddress.get()
    if checkVar.get() == 0:
        commGT.ProcessorSlot = int(selectedProcessorSlot.get())

    tags = None

    try:
        tags = commGT.GetTagList()

        if not tags is None:
            if not tags.Value is None:
                # save tags to a file
                if checkVarSaveTags.get() == 1:
                    with open('tags_list.txt', 'w') as f:
                        for t in tags.Value:
                            if t.DataType == '':
                                f.write(t.TagName + '\n')
                            else:
                                f.write(t.TagName + ' (DataType - ' + t.DataType + ')\n')

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
    except:
        commGT.Close()
        commGT = None

def comm_check():
    global comm
    global updateRunning
    global connected
    global connectionInProgress

    connectionInProgress = True
    ip = selectedIPAddress.get()
    port = int(selectedProcessorSlot.get())

    if (not connected or comm.IPAddress != ip or comm.ProcessorSlot != port or changePLC.get() == 1):
        if not comm is None:
            comm.Close()
            comm = None

        comm = PLC()
        comm.IPAddress = ip

        if checkVar.get() == 0:
            comm.ProcessorSlot = port
            comm.Micro800 = False
        else:
            comm.Micro800 = True

        plcTime = comm.GetPLCTime()

        lbConnectionMessage.delete(0, 'end')
        lbErrorMessage.delete(0, 'end')

        if plcTime.Value is None:
            if btnStop['state'] == 'disabled':
                btnStart['state'] = 'disabled'
            lbConnectionMessage.insert(1, 'Not Connected')
            lbErrorMessage.insert(1, plcTime.Status)
            connected = False
            root.after(5000, start_connection)
        else:
            lbConnectionMessage.insert(1, 'Connected')
            connectionInProgress = False
            connected = True
            if btnStop['state'] == 'disabled':
                btnStart['state'] = 'normal'
                updateRunning = True
            else:
                start_update()

    changePLC.set(0)

def startUpdateValue():
    global updateRunning
    global connected
    global checkVarLogTagValues

    '''
    Call ourself to update the screen
    '''

    readArray = False
    arrayElementCount = 0

    if not connected:
        if not connectionInProgress:
            start_connection()
    else:
        if not updateRunning:
            updateRunning = True
        else:
            # remove all the spaces
            displayTag = (selectedTag.get()).replace(' ', '')

            if displayTag != '':
                myTag = []
                if ';' in displayTag:
                    tags = displayTag.split(';')
                    for tag in tags:
                        if not str(tag) == '':
                            myTag.append(str(tag))
                elif '{' in displayTag and '}' in displayTag: # array
                    try:
                        arrayElementCount = int(displayTag[displayTag.index('{') + 1:displayTag.index('}')])
                        readArray = True
                        myTag.append(displayTag[0:displayTag.index('{')])
                    except:
                        myTag.append(displayTag)
                else:
                    myTag.append(displayTag)

            try:
                if readArray and arrayElementCount > 0:
                    response = comm.Read(myTag[0], arrayElementCount)
                else:
                    response = comm.Read(myTag)
            except Exception as e:
                tagValue['text'] = str(e)
                response = None

            if not response is None:
                allValues = ''

                if readArray and arrayElementCount > 0:
                    if not response.Value is None:
                        for val in response.Value:
                            if val == '':
                                allValues += '{}, '
                            else:
                                allValues += str(val) + ', '
                else:
                    for tag in response:
                        if tag.Status == 'Success':
                            allValues += str(tag.Value) + ', '
                        elif tag.Status == 'Connection lost':
                            connected = False

                            lbConnectionMessage.delete(0, 'end')
                            lbConnectionMessage.insert(1, tag.Status)
                            lbErrorMessage.delete(0, 'end')
                            allValues = ''
                            tagValue['text'] = 'Connection lost'
                            break
                        else:
                            connected = False

                            lbErrorMessage.delete(0, 'end')
                            lbErrorMessage.insert(1, tag.Status)
                            allValues = ''
                            tagValue['text'] = '~'
                            break

                if allValues != '':
                    tagValue['text'] = allValues[:-2]
                    if checkVarLogTagValues.get() == 1:
                        with open('tag_values_log.txt', 'a') as log_file:
                            strValue = str(datetime.datetime.now()) + ': ' + allValues[:-2] + '\n'
                            log_file.write(strValue)

 
            if btnStart['state'] == 'normal':
                btnStart['state'] = 'disabled'
                btnStop['state'] = 'normal'
                tbIPAddress['state'] = 'disabled'
                if checkVar.get() == 0:
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

def save_tags_list(event, chbSaveTags):
    if checkVarSaveTags.get() == 0:
        popup_menu_save_tags_list.post(event.x_root, event.y_root)
        checkVarSaveTags.set(1)

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
