# See screenshots here: https://github.com/dmroeder/pylogix/issues/156

# This example allows reading either a single tag or multiple tags separated by semicolon (';').
# Single tag example: CT_2D_DINTArray[0,0] or CT_STRING or CT_BOOLArray[252].
# Multi tag example: CT_DINT; CT_REAL; CT_3D_DINTArray[0,3,1].

# It also allows reading multiple elements of an array with the following tag format: tagName[startIndex]{elementCount}
# where 'startIndex' is the starting array index (x or x,y or x,y,z) and 'elementCount' is the number of consecutive elements to read.
# Example: CT_REALArray[0]{15} or CT_DINTArray[0,1,0]{7}
# Multi tag example: CT_DINT; CT_DINT.0{5}; CT_REAL; CT_3D_DINTArray[0,3,1]; CT_DINTArray[0,1,0]{7}.

# Enabling logging will log values of the current tags
# Enabling logging will force bool/bit values to always be logged as True/False for uniformity of the log file
# Changing tags when logging is enabled will always overwrite the log file (save it manually if needed)
# Not changing tags when logging is enabled allows to Stop/Start updating of the values and continue appending them 

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

Window/widget resizing:
Reference: https://stackoverflow.com/questions/22835289/how-to-get-tkinter-canvas-to-dynamically-resize-to-window-width

'''

import os.path
import platform
import threading
import datetime
import pylogix

from pylogix import PLC

try:
    # Python 2
    from Tkinter import *
except ImportError:
    # Python 3
    from tkinter import *
    import tkinter.font as tkfont

pythonVersion = platform.python_version()

# width wise resizing of the tag label (window)
class LabelResizing(Label):
    def __init__(self,parent,**kwargs):
        Label.__init__(self,parent,**kwargs)
        self.bind("<Configure>", self.on_resize)
        self.width = self.winfo_reqwidth()

    def on_resize(self,event):
        if self.width > 0:
            self.width = int(event.width)
            self.config(width=self.width, wraplength=self.width)

# width wise resizing of the tag entry box (window)
class EntryResizing(Entry):
    def __init__(self,parent,**kwargs):
        Entry.__init__(self,parent,**kwargs)
        self.bind("<Configure>", self.on_resize)
        self.width = self.winfo_reqwidth()

    def on_resize(self,event):
        if self.width > 0:
            self.width = int(event.width)
            self.config(width=self.width)

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
myTag, ipAddress, processorSlot = ['CT_STRING', 'CT_REAL', 'CT_DINT', 'CT_DINT.2{7}'], '192.168.1.15', 3
headerAdded = False

ver = pylogix.__version__

def main():
    '''
    Create our window and comm driver
    '''
    global root
    global comm
    global checkVarMicro800
    global checkVarSaveTags
    global checkVarLogTagValues
    global checkVarBoolDisplay
    global selectedIPAddress
    global selectedProcessorSlot
    global chbMicro800
    global chbSaveTags
    global chbLogTagValues
    global chbBoolDisplay
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
    global regularTags
    global arrayTags
    global tagsSet
    global previousLogHeader
    global app_closing

    root = Tk()
    root.config(background='black')
    root.title('Pylogix GUI Test - Python v' + pythonVersion)
    root.geometry('800x600')
    root.bind('<Destroy>', on_exit)

    app_closing = False

    connectionInProgress, connected, updateRunning = False, False, True

    regularTags = []
    arrayTags = dict()

    previousLogHeader = ''
    tagsSet = False

    changePLC = IntVar()
    changePLC.set(0)

    # bind the 'q' keyboard key to quit
    root.bind('q', lambda event:root.destroy())

    # add a frame to hold top widgets
    frame1 = Frame(root, background='black')
    frame1.pack(side='top', fill=X)

    # add list boxes for Device Discovery and Get Tags
    lbDevices = Listbox(frame1, height=11, width=45, bg='lightblue')
    lbTags = Listbox(frame1, height=11, width=45, bg='lightgreen')

    lbDevices.pack(anchor='n', side='left', padx=3, pady=3)

    # add a scrollbar for the Devices list box
    scrollbarDevices = Scrollbar(frame1, orient='vertical', command=lbDevices.yview)
    scrollbarDevices.pack(anchor='n', side='left', pady=3, ipady=65)
    lbDevices.config(yscrollcommand = scrollbarDevices.set)

    # copy selected IP Address to the clipboard on the mouse double-click
    # this is currently set to work for IP Address only
    lbDevices.bind('<Double-Button-1>', lambda event: ip_copy())

    # add the Discover Devices button
    btnDiscoverDevices = Button(frame1, text = 'Discover Devices', fg ='green', height=1, width=14, command=start_discover_devices)
    btnDiscoverDevices.pack(anchor='n', side='left', padx=3, pady=3)

    # add a scrollbar for the Tags list box
    scrollbarTags = Scrollbar(frame1, orient='vertical', command=lbTags.yview)
    scrollbarTags.pack(anchor='n', side='right', padx=3, pady=3, ipady=65)
    lbTags.config(yscrollcommand = scrollbarTags.set)

    # copy selected tag to the clipboard on the mouse double-click
    lbTags.bind('<Double-Button-1>', lambda event: tag_copy())

    lbTags.pack(anchor='n', side='right', pady=3)

    # add the Get Tags button
    btnGetTags = Button(frame1, text = 'Get Tags', fg ='green', height=1, width=14, command=start_get_tags)
    btnGetTags.pack(anchor='n', side='right', padx=3, pady=3)

    # add a frame to hold the label for pylogix version and Log tag values/Save tags/Micro800 checkboxes
    frame2 = Frame(root, background='black')
    frame2.pack(fill=X)

    # create a label to show pylogix version
    lblVersion = Label(frame2, text='pylogix v' + ver, fg='grey', bg='black', font='Helvetica 9')
    lblVersion.pack(side='left', padx=3, pady=5)

    # add 'Log tag values' checkbox
    checkVarLogTagValues = IntVar()
    chbLogTagValues = Checkbutton(frame2, text='Log tags values', variable=checkVarLogTagValues, command=setBoolDisplayForLogging)
    checkVarLogTagValues.set(0)
    chbLogTagValues.pack(side='left', padx=95, pady=4)

    # add Micro800 checkbox
    checkVarMicro800 = IntVar()
    chbMicro800 = Checkbutton(frame2, text='PLC is Micro800', variable=checkVarMicro800, command=check_micro800)
    checkVarMicro800.set(0)
    chbMicro800.pack(side='right', padx=5, pady=4)

    # add 'Save tags' checkbox
    checkVarSaveTags = IntVar()
    chbSaveTags = Checkbutton(frame2, text='Save tags list', variable=checkVarSaveTags)
    checkVarSaveTags.set(0)
    chbSaveTags.pack(side='right', padx=80, pady=4)

    # add the tooltip menu on the mouse right-click
    popup_menu_save_tags_list = Menu(chbSaveTags, bg='lightblue', tearoff=0)
    popup_menu_save_tags_list.add_command(label='Click the Get Tags button to save the list', command=set_checkbox_state)
    chbSaveTags.bind('<Button-1>', lambda event: save_tags_list(event, chbSaveTags))

    # add a frame to hold connection and error messages listboxes
    frame3 = Frame(root, background='black')
    frame3.pack(side='bottom', fill=X)

    # add a list box for connection messages
    lbConnectionMessage = Listbox(frame3, height=1, width=45, fg='blue', bg='lightgrey')
    lbConnectionMessage.pack(anchor=S, side='left', padx=3, pady=3)

    # add a listbox for error messages
    lbErrorMessage = Listbox(frame3, height=1, width=45, fg='red', bg='lightgrey')
    lbErrorMessage.pack(anchor=S, side='right', padx=3, pady=3)

    # add a frame to hold the tag label, tag entry box and the update buttons
    frame4 = Frame(root, background='black')
    frame4.pack(fill=X)

    # create a label for the Tag entry
    lblTag = Label(frame4, text='Tags To Read (separate with semicolon)', fg='white', bg='black', font='Helvetica 8')
    lblTag.pack(anchor='center', pady=10)

    # add button to start updating tag value
    btnStart = Button(frame4, text = 'Start Update', state='disabled', bg='lightgrey', fg ='blue', height=1, width=10, command=start_update)
    btnStart.pack(side='left', padx=5, pady=1)

    # add button to stop updating tag value
    btnStop = Button(frame4, text = 'Stop Update', state='disabled', fg ='blue', height=1, width=10, command=stopUpdateValue)
    btnStop.pack(side='right', padx=5, pady=1)

    # create a text box for the Tag entry
    char_width = 5

    if int(pythonVersion[0]) > 2:
        fnt = tkfont.Font(family="Helvetica", size=11, weight="normal")
        char_width = fnt.measure("0")
    
    selectedTag = StringVar()
    tbTag = EntryResizing(frame4, justify='center', textvariable=selectedTag, font='Helvetica 11', width=(int(800 / char_width) - 24))
    selectedTag.set((str(myTag).replace(',', ';'))[1:-1].replace('\'', ''))

    # add the 'Paste' menu on the mouse right-click
    popup_menu_tbTag = Menu(tbTag, tearoff=0)
    popup_menu_tbTag.add_command(label='Paste', command=tag_paste)
    tbTag.bind('<Button-3>', lambda event: tag_menu(event, tbTag))

    tbTag.pack(side='left', fill=X)

    # add a frame to hold the label displaying the tag value
    frame5 = Frame(root, background='black')
    frame5.pack(fill=X)

    # create a label to display the tag value
    if int(pythonVersion[0]) > 2:
        fnt = tkfont.Font(family="Helvetica", size=11, weight="normal")
        char_width = fnt.measure("0")
    
    tagValue = LabelResizing(frame5, text='~', justify='left', fg='yellow', bg='navy', font='Helvetica 18', width=(int(800 / char_width - 4.5)), wraplength=800, relief=SUNKEN)
    tagValue.pack(anchor='center', padx=3, pady=5)

    # add a frame to hold the IPAddress / Slot labels
    frameIPSlotLabels = Frame(root, background='black')
    frameIPSlotLabels.place(anchor='center', relx=0.5, rely=0.09)

    # create a label for the IPAddress entry
    lblIPAddress = Label(frameIPSlotLabels, text='IP Address', fg='white', bg='black', font='Helvetica 8')
    lblIPAddress.pack(side='left', anchor='n', padx=32)

    # create a label for the processor Slot entry
    lblProcessorSlot = Label(frameIPSlotLabels, text='Slot', fg='white', bg='black', font='Helvetica 8')
    lblProcessorSlot.pack(side='left', anchor='n', padx=8)

    # add a frame to hold the IPAddress / Slot entry boxes
    frameIPSlotBoxes = Frame(root, background='black')
    frameIPSlotBoxes.place(anchor='center', relx=0.5, rely=0.12)

    # create a text box for the IPAddress entry
    selectedIPAddress = StringVar()
    tbIPAddress = Entry(frameIPSlotBoxes, justify='center', textvariable=selectedIPAddress)
    selectedIPAddress.set(ipAddress)

    # add the 'Paste' menu on the mouse right-click
    popup_menu_tbIPAddress = Menu(tbIPAddress, tearoff=0)
    popup_menu_tbIPAddress.add_command(label='Paste', command=ip_paste)
    tbIPAddress.bind('<Button-3>', lambda event: ip_menu(event, tbIPAddress))

    tbIPAddress.pack(side='left', anchor='n', padx=1, pady=1)

    # create a spinbox for the processor Slot entry
    selectedProcessorSlot = StringVar()
    sbProcessorSlot = Spinbox(frameIPSlotBoxes, width=4, justify='center', from_ = 0, to = 17, increment=1, textvariable=selectedProcessorSlot, state='readonly')
    selectedProcessorSlot.set(processorSlot)
    sbProcessorSlot.pack(side='right', anchor='n', padx=1, pady=1)

    # add a frame to hold the Boolean Display checkbox
    frameBoolDisplay = Frame(root, background='black')
    frameBoolDisplay.place(anchor='center', relx=0.5, rely=0.2)

    # add 'Boolean Display' checkbox
    checkVarBoolDisplay = IntVar()
    chbBoolDisplay = Checkbutton(frameBoolDisplay, text='Boolean Display 1 : 0', variable=checkVarBoolDisplay)
    checkVarBoolDisplay.set(0)
    chbBoolDisplay.pack(side='top', anchor='center', pady=3)

    # add Exit button
    btnExit = Button(root, text = 'Exit', fg ='red', height=1, width=10, command=root.destroy)
    btnExit.place(anchor='center', relx=0.5, rely=0.98)

    # set the minimum window size to the current size
    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())

    comm = None

    start_connection()

    root.mainloop()

    try:
        if not comm is None:
            comm.Close()
            comm = None
    except:
        pass

def on_exit(*args):
    global app_closing

    app_closing = True

def start_connection():
    try:
        thread1 = connection_thread()
        thread1.setDaemon(True)
        thread1.start()
    except Exception as e:
        print('unable to start connection_thread, ' + str(e))

def start_discover_devices():
    try:
        thread2 = device_discovery_thread()
        thread2.setDaemon(True)
        thread2.start()
    except Exception as e:
        print('unable to start device_discovery_thread, ' + str(e))

def start_get_tags():
    try:
        thread3 = get_tags_thread()
        thread3.setDaemon(True)
        thread3.start()
    except Exception as e:
        print('unable to start get_tags_thread, ' + str(e))

def start_update():
    try:
        thread4 = update_thread()
        thread4.setDaemon(True)
        thread4.start()
    except Exception as e:
        print('unable to start update_thread, ' + str(e))

def check_micro800():
    if checkVarMicro800.get() == 1:
        sbProcessorSlot['state'] = 'disabled'
    else:
        sbProcessorSlot['state'] = 'normal'

    changePLC.set(1)
    lbDevices.delete(0, 'end')
    lbTags.delete(0, 'end')
    start_connection()

def setBoolDisplayForLogging():
    global checkVarBoolDisplay

    if checkVarLogTagValues.get() == 1: # force logging bool/bit values as True/False for uniformity
        checkVarBoolDisplay.set(0)
        chbBoolDisplay['state'] = 'disabled'
    else:
        chbBoolDisplay['state'] = 'normal'

def discoverDevices():
    try:
        lbDevices.delete(0, 'end')

        commDD = PLC()

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
                lbDevices.insert(i * 12 + 9, 'Serial: ' + str(int(device.SerialNumber, 0)))
                lbDevices.insert(i * 12 + 10, 'State: ' + str(device.State))
                lbDevices.insert(i * 12 + 11, 'Status: ' + str(device.Status))
                lbDevices.insert(i * 12 + 12, '----------------------------------')
                i += 1

            for device in devices.Value:
                if device.DeviceID == 14:
                    lbDevices.insert(i * 12 + 1, 'Modules at ' + device.IPAddress)

                    '''
                    Query each slot for a module
                    '''
                    with PLC() as c:
                        c.IPAddress = device.IPAddress

                        for j in range(17):
                            x = c.GetModuleProperties(j)
                            lbDevices.insert(i * 12 + 2 + j, 'Slot ' + str(j) + ' ' + x.Value.ProductName + ' rev: ' + x.Value.Revision)

                    c.Close()
                    c = None

                    i += 1

        commDD.Close()
        commDD = None
    except Exception as e:
        if not commDD is None:
            commDD.Close()
            commDD = None

        if app_closing:
            pass
        else:
            print(str(e))

def getTags():
    try:
        lbTags.delete(0, 'end')

        commGT = PLC()
        commGT.IPAddress = selectedIPAddress.get()
        if checkVarMicro800.get() == 0:
            commGT.ProcessorSlot = int(selectedProcessorSlot.get())

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
    except Exception as e:
        if not commGT is None:
            commGT.Close()
            commGT = None

        if app_closing:
            pass
        else:
            print(str(e))

def comm_check():
    global comm
    global updateRunning
    global connected
    global connectionInProgress

    try:
        connectionInProgress = True
        ip = selectedIPAddress.get()
        port = int(selectedProcessorSlot.get())

        if (not connected or comm.IPAddress != ip or comm.ProcessorSlot != port or changePLC.get() == 1):
            if not comm is None:
                comm.Close()
                comm = None

            comm = PLC()
            comm.IPAddress = ip

            if checkVarMicro800.get() == 0:
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
                    btnStart['bg'] = 'lightgrey'
                lbConnectionMessage.insert(1, ' Not Connected')
                lbErrorMessage.insert(1, ' ' + plcTime.Status)
                connected = False
                root.after(5000, start_connection)
            else:
                lbConnectionMessage.insert(1, ' Connected')
                if not updateRunning:
                    updateRunning = True

                connected = True
                connectionInProgress = False

                if btnStop['state'] == 'disabled':
                    btnStart['state'] = 'normal'
                    btnStart['bg'] = 'lightgreen'
                else:
                    start_update()

        changePLC.set(0)
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def startUpdateValue():
    global comm
    global updateRunning
    global connected
    global checkVarLogTagValues
    global previousLogHeader
    global headerAdded
    global regularTags
    global arrayTags
    global tagsSet

    '''
    Call ourself to update the screen
    '''

    try:
        tagsChanged = False
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
                allValues = ''
                logHeader = ''
                logValues = ''

                if displayTag != '':
                    chbLogTagValues['state'] = 'disabled'

                    if not tagsSet:
                        regularTags = []
                        arrayTags = dict()

                        if ';' in displayTag:
                            tags = displayTag.split(';')
                            for tag in tags:
                                t = str(tag)

                                if not t == '':
                                    if t.endswith('}') and '{' in t: # 1 or 2 or 3 dimensional array tag
                                        try:
                                            arrayElementCount = int(t[t.index('{') + 1:t.index('}')])

                                            if arrayElementCount < 2:
                                                regularTags.append(t[:t.index('{')])
                                            else:
                                                t = t[:t.index('{')]
                                                arrayTags.update( {t : arrayElementCount} )
                                        except:
                                            regularTags.append(t[:t.index('{')])
                                    else:
                                        regularTags.append(t)
                        elif displayTag.endswith('}') and '{' in displayTag: # 1 or 2 or 3 dimensional array tag
                            try:
                                arrayElementCount = int(displayTag[displayTag.index('{') + 1:displayTag.index('}')])

                                if arrayElementCount < 2:
                                    regularTags.append(displayTag[:displayTag.index('{')])
                                else:
                                    readArray = True
                                    arrayTags.update( {displayTag[:displayTag.index('{')] : arrayElementCount} )
                            except:
                                regularTags.append(displayTag[:displayTag.index('{')])
                        else:
                            regularTags.append(displayTag)

                        if len(regularTags) > 0:
                            for i in range(0, len(regularTags)):
                                logHeader += regularTags[i] + ', '

                        if len(arrayTags) > 0:
                            for key in arrayTags:
                                logHeader += key + '{' + str(arrayTags[key]) + '}, '

                        tagsSet = True
                        if previousLogHeader != logHeader:
                            tagsChanged = True

                    try:
                        if len(regularTags) > 0:
                            response = comm.Read(regularTags)

                            if not response[0].Value is None:
                                for i in range(0, len(response)):
                                    allValues += response[i].TagName + ' : '

                                    if (checkVarBoolDisplay.get() == 1) and (str(response[i].Value) == 'True' or str(response[i].Value) == 'False'):
                                        if checkVarLogTagValues.get() == 1:
                                            logValues += '1, ' if str(response[i].Value) == 'True' else '0, '

                                        allValues += '1, ' if str(response[i].Value) == 'True' else '0, '
                                    else:
                                        if str(response[i].Value) == '':
                                            if checkVarLogTagValues.get() == 1:
                                                logValues += '{}, '

                                            allValues += '{}, '
                                        else:
                                            if checkVarLogTagValues.get() == 1:
                                                logValues += str(response[i].Value) + ', '

                                            allValues += str(response[i].Value)

                                    allValues += '\n'

                        if len(arrayTags) > 0:
                            for tg in arrayTags:
                                response = comm.Read(tg, arrayTags[tg])

                                if not response.Value is None:
                                    allValues += response.TagName + '{' + str(arrayTags[tg]) + '} : '

                                    if (checkVarBoolDisplay.get() == 1) and (str(response.Value[0]) == 'True' or str(response.Value[0]) == 'False'):
                                        newBoolArray = []
                                        for val in range(0, len(response.Value)):
                                            newBoolArray.append(1 if str(response.Value[val]) == 'True' else 0)

                                        if checkVarLogTagValues.get() == 1:
                                            logValues += str(newBoolArray).replace(',', ';') + ', '

                                        allValues += str(newBoolArray)
                                    else:
                                        if checkVarLogTagValues.get() == 1:
                                            logValues += str(response.Value).replace(',', ';') + ', '

                                        allValues += str(response.Value)

                                    allValues += '\n'
                    except Exception as e:
                        tagValue['text'] = str(e)
                        connected = False
                        response = None
                        setWidgetState()
                        start_connection()
                        return

                    if allValues != '':
                        tagValue['text'] = allValues[:-1]
                        if checkVarLogTagValues.get() == 1:
                            if not os.path.exists('tag_values_log.txt') or tagsChanged:
                                headerAdded = False

                            if headerAdded:
                                with open('tag_values_log.txt', 'a') as log_file:
                                    strValue = str(datetime.datetime.now()).replace(' ', '/') + ', ' + logValues[:-2] + '\n'
                                    log_file.write(strValue)
                            else:
                                with open('tag_values_log.txt', 'w') as log_file:
                                    previousLogHeader = logHeader
                                    # add header with 'Date / Time' and all the tags being read
                                    header = 'Date / Time, ' + logHeader[:-2] + '\n'
                                    log_file.write(header)
                                    headerAdded = True
                    else:
                        plcTime = comm.GetPLCTime()
                        if plcTime.Value is None:
                            tagValue['text'] = 'Connection Lost'
                            if not connectionInProgress:
                                connected = False
                                start_connection()
                        else:
                            tagValue['text'] = 'Check Tag(s)'

                setWidgetState()

                root.after(500, startUpdateValue)
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def setWidgetState():
    try:
        if btnStart['state'] == 'normal':
            btnStart['state'] = 'disabled'
            btnStart['bg'] = 'lightgrey'
            btnStop['state'] = 'normal'
            btnStop['bg'] = 'lightgreen'
            tbIPAddress['state'] = 'disabled'
            if checkVarMicro800.get() == 0:
                sbProcessorSlot['state'] = 'disabled'
            chbMicro800['state'] = 'disabled'
            tbTag['state'] = 'disabled'
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def stopUpdateValue():
    global updateRunning
    global tagsSet

    try:
        if updateRunning:
            updateRunning = False
            tagValue['text'] = '~'
            chbLogTagValues['state'] = 'normal'
            if not connectionInProgress:
                btnStart['state'] = 'normal'
                btnStart['bg'] = 'lightgreen'
            btnStop['state'] = 'disabled'
            btnStop['bg'] = 'lightgrey'
            tbIPAddress['state'] = 'normal'
            chbMicro800['state'] = 'normal'
            if checkVarMicro800.get() == 0:
                sbProcessorSlot['state'] = 'normal'
            tbTag['state'] = 'normal'
            tagsSet = False
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def save_tags_list(event, chbSaveTags):
    if checkVarSaveTags.get() == 0:
        popup_menu_save_tags_list.post(event.x_root, event.y_root)
        # Windows users can also click outside of the popup so set the checkbox state here
        if platform.system() == 'Windows':
            chbSaveTags.select()

def set_checkbox_state():
    chbSaveTags.select()

def tag_copy():
    root.clipboard_clear()
    listboxSelectedTag = (lbTags.get(ANCHOR)).split(' ')[0]
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
    # user clicked the 'Paste' option so paste the tag from the clipboard
    selectedTag.set(root.clipboard_get())
    tbTag.select_range(0, 'end')
    tbTag.icursor('end')

def ip_copy():
    if (lbDevices.get(ANCHOR)).split(' ')[0] == 'IP':
        root.clipboard_clear()
        listboxSelectedIPAddress = (lbDevices.get(ANCHOR)).split(' ')[2]
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
    # user clicked the 'Paste' option so paste the IP Address from the clipboard
    selectedIPAddress.set(root.clipboard_get())
    tbIPAddress.select_range(0, 'end')
    tbIPAddress.icursor('end')

if __name__=='__main__':
    main()
